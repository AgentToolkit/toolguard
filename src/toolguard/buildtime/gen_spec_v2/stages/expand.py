"""The ``expand`` stage: repeated passes for rules ``create`` missed."""

from typing import List

from loguru import logger

from toolguard.buildtime.gen_spec.data_types import ToolInfo
from toolguard.buildtime.gen_spec_v2 import prompts
from toolguard.buildtime.gen_spec_v2.context import GenContext
from toolguard.buildtime.gen_spec_v2.models import PolicyItemV2, slugify
from toolguard.buildtime.gen_spec_v2.stages._shared import (
    build_item,
    dict_list,
    item_summary,
    messages,
)
from toolguard.buildtime.llm import I_TG_LLM


async def run_expand(
    llm: I_TG_LLM,
    ctx: GenContext,
    tool: ToolInfo,
    items: List[PolicyItemV2],
    iterations: int,
) -> List[PolicyItemV2]:
    """Ask for additional items up to ``iterations`` times, stopping when dry.

    Each pass sees what is already captured, so it looks for gaps rather than
    restating. A pass that adds nothing ends the loop: further passes over the
    same inputs would only repeat it.
    """
    items = list(items)
    taken = {item.id for item in items}

    for iteration in range(max(0, iterations)):
        response = await llm.chat_json(
            messages(
                prompts.system("expand"),
                prompts.expand_user(ctx, tool, [item_summary(i) for i in items]),
            )
        )

        new_items: List[PolicyItemV2] = []
        for raw in dict_list(response, "policy_items"):
            candidate_slug = slugify(raw.get("slug") or raw.get("name") or "")
            if candidate_slug and f"{tool.name}.{candidate_slug}" in taken:
                continue
            item = build_item(raw, tool.name, taken)
            if item is None:
                continue
            new_items.append(item)

        if not new_items:
            logger.debug(
                "expand({}): pass {} found nothing new, stopping",
                tool.name,
                iteration + 1,
            )
            break

        items.extend(new_items)
        logger.debug(
            "expand({}): pass {} added {}", tool.name, iteration + 1, len(new_items)
        )

    return items
