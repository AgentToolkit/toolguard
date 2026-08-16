"""The review stage: several independent votes on whether a rule belongs here.

Review answers two questions per item -- is this rule relevant to this tool, and
can it be validated at all -- and keeps the item only on a strict majority of
both. It is the stage that removes rules the spec format deliberately cannot
express: a rule bound to the wrong tool, an orchestration-level rule with no
tool to attach to, a foreign-domain rule, a bare permit with nothing to deny, or
a definition mistaken for a rule.

That removal is load-bearing rather than merely tidy. Orphan guidance is found
by diffing the policy document against the text the references quote, so an item
that quoted an orchestration rule would make that rule look covered.
"""

from __future__ import annotations

import asyncio
from typing import List, Sequence, Tuple

from toolguard.buildtime.gen_spec.data_types import ToolInfo
from toolguard.buildtime.gen_spec_v2.context import GenContext
from toolguard.buildtime.gen_spec_v2.data_types import PolicyItemV2, RejectedItem
from toolguard.buildtime.gen_spec_v2.prompts import review as review_prompt
from toolguard.buildtime.gen_spec_v2.utils import ask_json
from toolguard.buildtime.llm import I_TG_LLM

STAGE = "review"


def tally(votes: Sequence[dict]) -> Tuple[bool, str]:
    """Combine review votes into one keep/drop decision plus the joined reasons.

    An item is kept when the mean of ``is_relevant AND can_be_validated`` across
    votes is strictly greater than 0.5 -- so a tie drops the item, and no votes
    at all drops it. A vote missing either key counts as a no rather than
    raising.
    """
    scores = [
        1.0 if (vote.get("is_relevant") and vote.get("can_be_validated")) else 0.0
        for vote in votes
    ]
    mean = sum(scores) / len(scores) if scores else 0.0
    reasons: List[str] = [str(vote["reason"]) for vote in votes if vote.get("reason")]
    return mean > 0.5, " ".join(reasons)


async def _review_item(
    llm: I_TG_LLM,
    ctx: GenContext,
    tool: ToolInfo,
    item: PolicyItemV2,
    n_votes: int,
) -> Tuple[bool, str]:
    payload = {"id": item.id, "name": item.name, "description": item.description}
    votes = await asyncio.gather(
        *[
            ask_json(llm, review_prompt.SYSTEM, review_prompt.user(ctx, tool, payload))
            for _ in range(n_votes)
        ]
    )
    return tally(list(votes))


async def run_review(
    llm: I_TG_LLM,
    ctx: GenContext,
    tool: ToolInfo,
    items: Sequence[PolicyItemV2],
    n_votes: int,
) -> Tuple[List[PolicyItemV2], List[RejectedItem]]:
    """Vote on every item concurrently; split them into survivors and rejects."""
    verdicts = await asyncio.gather(
        *[_review_item(llm, ctx, tool, item, n_votes) for item in items]
    )

    kept: List[PolicyItemV2] = []
    rejected: List[RejectedItem] = []
    for item, (keep, reason) in zip(items, verdicts):
        if keep:
            kept.append(item)
        else:
            rejected.append(RejectedItem(item=item, reason=reason, stage=STAGE))
    return kept, rejected
