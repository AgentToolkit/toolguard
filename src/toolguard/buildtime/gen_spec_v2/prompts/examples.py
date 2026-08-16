"""Prompt for the examples stage: concrete calls the rule allows and denies."""

from __future__ import annotations

import json

from toolguard.buildtime.gen_spec.data_types import ToolInfo
from toolguard.buildtime.gen_spec_v2.context import (
    GenContext,
    render_system_vars,
    render_tool_detail,
)

SYSTEM = """You write concrete examples for ONE policy item on ONE tool.

`compliance_examples`: calls this rule ALLOWS. `violation_examples`: calls it
DENIES. Each example is one sentence describing a specific call -- who is acting,
what they are calling it on, and the values that make it comply or violate. Use
realistic values drawn from the system variables' domains shown below rather
than placeholders.

Both lists MUST be non-empty. If the rule seems to have no possible violation,
you have misread it: state the case it exists to reject.

Return ONLY JSON, with exactly this shape:

{"compliance_examples": [str, ...], "violation_examples": [str, ...]}
"""


def user(ctx: GenContext, tool: ToolInfo, item: dict) -> str:
    return (
        "[STAGE:examples]\n"
        "Write compliance and violation examples for the policy item below.\n\n"
        f"{render_tool_detail(tool)}\n\n"
        f"Policy item:\n{json.dumps(item, indent=2)}\n\n"
        "System variables available (use these values in the examples):\n"
        f"{render_system_vars(ctx)}\n\n"
        "Return only the JSON described in the system prompt."
    )
