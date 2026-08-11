"""The ``review`` stage: repeated relevance votes with a majority tally."""

import asyncio
from typing import Any, Dict, List, Sequence, Tuple

from loguru import logger

from toolguard.buildtime.gen_spec.data_types import ToolInfo
from toolguard.buildtime.gen_spec_v2 import prompts
from toolguard.buildtime.gen_spec_v2.context import GenContext
from toolguard.buildtime.gen_spec_v2.models import PolicyItemV2
from toolguard.buildtime.gen_spec_v2.stages._shared import item_summary, messages
from toolguard.buildtime.llm import I_TG_LLM


def tally(votes: Sequence[Any]) -> Tuple[bool, str]:
    """Keep the item when a strict majority of votes approve it on both counts.

    A vote missing either verdict counts against keeping: an item nobody could
    confirm is relevant and checkable does not belong in the spec.
    """
    usable = [v for v in votes if isinstance(v, dict)]
    if not usable:
        return False, ""

    approvals = sum(
        1
        for v in usable
        if v.get("is_relevant") is True and v.get("can_be_validated") is True
    )
    reasons = " ".join(
        str(v.get("reason", "")).strip() for v in usable if v.get("reason")
    )
    return approvals * 2 > len(usable), reasons


async def _review_item(
    llm: I_TG_LLM, ctx: GenContext, tool: ToolInfo, item: PolicyItemV2, votes: int
) -> Tuple[bool, str]:
    system = prompts.system("review")
    user = prompts.review_user(ctx, tool, item_summary(item))
    results = await asyncio.gather(
        *[llm.chat_json(messages(system, user)) for _ in range(votes)]
    )
    return tally(list(results))


async def run_review(
    llm: I_TG_LLM,
    ctx: GenContext,
    tool: ToolInfo,
    items: List[PolicyItemV2],
    votes: int,
) -> Tuple[List[PolicyItemV2], List[Dict[str, Any]]]:
    """Split ``items`` into survivors and archive entries.

    Archive entries keep the item's references so a later reader can see which
    part of the policy document was considered and set aside.
    """
    if not items:
        return [], []

    results = await asyncio.gather(
        *[_review_item(llm, ctx, tool, item, votes) for item in items]
    )

    kept: List[PolicyItemV2] = []
    archived: List[Dict[str, Any]] = []
    for item, (keep, reason) in zip(items, results):
        if keep:
            kept.append(item)
            continue
        logger.debug("{}: archived by review — {}", item.id, reason)
        archived.append(
            {
                "id": item.id,
                "name": item.name,
                "reason": reason,
                "stage": "review",
                "references": list(item.references),
            }
        )

    return kept, archived
