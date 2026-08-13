"""The ``create`` stage: bind the policy document's rules to one tool."""

from typing import List, Tuple

from loguru import logger

from toolguard.buildtime.gen_spec.data_types import ToolInfo
from toolguard.buildtime.gen_spec_v2 import prompts
from toolguard.buildtime.gen_spec_v2.context import GenContext
from toolguard.buildtime.gen_spec_v2.models import PolicyItemV2, SpecToolInfo
from toolguard.buildtime.gen_spec_v2.stages._shared import (
    build_item,
    dict_list,
    messages,
)
from toolguard.buildtime.llm import I_TG_LLM


async def run_create(
    llm: I_TG_LLM, ctx: GenContext, tool: ToolInfo
) -> Tuple[SpecToolInfo, List[PolicyItemV2]]:
    """Bind every applicable rule to ``tool`` in one call.

    Returns what the model learned about the tool itself, plus one item per
    grounded rule with placeholder trigger/requires/examples for the later
    stages to fill in.
    """
    response = await llm.chat_json(
        messages(prompts.system("create"), prompts.create_user(ctx, tool))
    )

    raw_info = response.get("tool_info") if isinstance(response, dict) else None
    tool_info = SpecToolInfo()
    if isinstance(raw_info, dict):
        tool_info = SpecToolInfo(
            is_read_only=bool(raw_info.get("is_read_only", False)),
            user_enrichment=str(raw_info.get("user_enrichment", "") or ""),
        )

    taken: set = set()
    items: List[PolicyItemV2] = []
    for raw in dict_list(response, "policy_items"):
        item = build_item(raw, tool.name, taken)
        if item is None:
            logger.debug("{}: dropping ungrounded or unnamed create item", tool.name)
            continue
        items.append(item)

    logger.debug("create({}): {} item(s)", tool.name, len(items))
    return tool_info, items
