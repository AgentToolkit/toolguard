"""The ``examples`` stage: concrete compliance and violation scenarios.

Examples are what the code generator's test generation works from, so they run
last — after ``enrich``, so an example for a ``post_tool`` rule can talk about
the result rather than the arguments.
"""

import asyncio
from typing import List, Optional

from toolguard.buildtime.gen_spec.data_types import ToolInfo
from toolguard.buildtime.gen_spec_v2 import prompts
from toolguard.buildtime.gen_spec_v2.context import GenContext
from toolguard.buildtime.gen_spec_v2.models import PolicyItemV2
from toolguard.buildtime.gen_spec_v2.stages._shared import (
    item_summary,
    messages,
    str_list,
)
from toolguard.buildtime.llm import I_TG_LLM


async def run_examples(
    llm: I_TG_LLM,
    ctx: GenContext,
    tool: ToolInfo,
    items: List[PolicyItemV2],
    example_number: Optional[int] = None,
) -> None:
    """Write examples onto each item in place.

    ``example_number`` of ``None`` lets the model choose how many; a positive
    number asks for exactly that many of each.
    """
    if not items:
        return

    system = prompts.system("examples")

    async def for_item(item: PolicyItemV2) -> None:
        summary = item_summary(item)
        summary["trigger"] = item.trigger.value
        user = prompts.examples_user(ctx, tool, summary)
        if example_number:
            user += (
                f"\n\nWrite exactly {example_number} compliance example(s) and "
                f"exactly {example_number} violation example(s)."
            )

        response = await llm.chat_json(messages(system, user))
        if not isinstance(response, dict):
            return
        item.compliance_examples = str_list(response.get("compliance_examples"))
        item.violation_examples = str_list(response.get("violation_examples"))

    await asyncio.gather(*[for_item(item) for item in items])
