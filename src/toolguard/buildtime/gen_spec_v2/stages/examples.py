"""The examples stage: one compliance and one violation example per rule, at least.

This is phase 2 of generation, deliberately separable from policy creation so the
two can be run and reviewed independently. The spec schema requires both example
lists to be non-empty, so a spec is only valid once this stage has run: an item
whose examples stay empty after a retry is rejected rather than written.
"""

from __future__ import annotations

import asyncio
from typing import List, Sequence, Tuple

from loguru import logger

from toolguard.buildtime.gen_spec.data_types import ToolInfo
from toolguard.buildtime.gen_spec_v2.context import GenContext
from toolguard.buildtime.gen_spec_v2.data_types import PolicyItemV2, RejectedItem
from toolguard.buildtime.gen_spec_v2.prompts import examples as examples_prompt
from toolguard.buildtime.gen_spec_v2.utils import ask_json
from toolguard.buildtime.llm import I_TG_LLM

STAGE = "examples"
EMPTY_REASON = "no compliance or violation example could be generated"


def _string_list(value: object) -> List[str]:
    if not isinstance(value, list):
        return []
    return [entry for entry in value if isinstance(entry, str) and entry.strip()]


async def _examples_for_item(
    llm: I_TG_LLM,
    ctx: GenContext,
    tool: ToolInfo,
    item: PolicyItemV2,
    attempts: int = 2,
) -> bool:
    """Fill one item's examples, retrying while either side is empty.

    Returns whether the item ended up with at least one of each.
    """
    payload = {"id": item.id, "name": item.name, "description": item.description}
    for attempt in range(attempts):
        response = await ask_json(
            llm, examples_prompt.SYSTEM, examples_prompt.user(ctx, tool, payload)
        )
        compliance = _string_list(response.get("compliance_examples"))
        violation = _string_list(response.get("violation_examples"))
        if compliance and violation:
            item.compliance_examples = compliance
            item.violation_examples = violation
            return True
        logger.warning(
            f"examples({item.id}): attempt {attempt + 1} produced "
            f"{len(compliance)} compliance / {len(violation)} violation examples"
        )
    item.compliance_examples = []
    item.violation_examples = []
    return False


async def run_examples(
    llm: I_TG_LLM,
    ctx: GenContext,
    tool: ToolInfo,
    items: Sequence[PolicyItemV2],
) -> Tuple[List[PolicyItemV2], List[RejectedItem]]:
    """Fill examples for every item concurrently; split off the ones left empty."""
    outcomes = await asyncio.gather(
        *[_examples_for_item(llm, ctx, tool, item) for item in items]
    )

    kept: List[PolicyItemV2] = []
    rejected: List[RejectedItem] = []
    for item, ok in zip(items, outcomes):
        if ok:
            kept.append(item)
        else:
            rejected.append(RejectedItem(item=item, reason=EMPTY_REASON, stage=STAGE))
    return kept, rejected
