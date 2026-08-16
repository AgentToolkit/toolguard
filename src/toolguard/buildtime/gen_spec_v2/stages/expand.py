"""The expand stage: repeated passes looking for rules the create stage missed."""

from __future__ import annotations

from typing import List

from loguru import logger

from toolguard.buildtime.gen_spec.data_types import ToolInfo
from toolguard.buildtime.gen_spec_v2.context import GenContext
from toolguard.buildtime.gen_spec_v2.data_types import PolicyItemV2
from toolguard.buildtime.gen_spec_v2.prompts import expand as expand_prompt
from toolguard.buildtime.gen_spec_v2.stages.create import build_items
from toolguard.buildtime.gen_spec_v2.utils import ask_json
from toolguard.buildtime.llm import I_TG_LLM


async def run_expand(
    llm: I_TG_LLM,
    ctx: GenContext,
    tool: ToolInfo,
    items: List[PolicyItemV2],
    max_iterations: int,
) -> List[PolicyItemV2]:
    """Ask for missed rules up to ``max_iterations`` times.

    Stops as soon as a pass adds nothing, which is the normal outcome once the
    create stage did its job -- there is no point paying for the remaining
    passes. Ids stay unique across passes, and an item without a reference is
    dropped just as in create.
    """
    items = list(items)
    taken = {item.id for item in items}

    for iteration in range(max_iterations):
        captured = [
            {"id": item.id, "name": item.name, "description": item.description}
            for item in items
        ]
        response = await ask_json(
            llm, expand_prompt.SYSTEM, expand_prompt.user(ctx, tool, captured)
        )
        new_items = build_items(response.get("policy_items") or [], tool.name, taken)
        if not new_items:
            logger.debug(
                f"expand({tool.name}): nothing new on pass {iteration + 1}, stopping"
            )
            break
        items.extend(new_items)

    return items
