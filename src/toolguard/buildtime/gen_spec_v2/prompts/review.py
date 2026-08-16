"""Prompt for the review stage: is this rule relevant here, and checkable at all."""

from __future__ import annotations

import json

from toolguard.buildtime.gen_spec.data_types import ToolInfo
from toolguard.buildtime.gen_spec_v2.context import (
    GenContext,
    render_policy_rules,
    render_system_vars,
    render_tool_detail,
    render_tools_overview,
)

SYSTEM = """You judge whether ONE policy item belongs on ONE tool.

Answer two questions independently.

`is_relevant`: does this rule actually govern or constrain THIS tool's call or
its result? Answer false when the rule governs a different tool, describes the
agent's own orchestration rather than a tool call, comes from another
application domain, merely grants permission with nothing to deny, or is a
definition of a term rather than a rule.

`can_be_validated`: could a deterministic guard decide this rule, given this
tool's arguments and result, the system variables listed below, the result of a
prior read-only tool call from the tool catalog, and the conversation history?
Answer true even when the check would need one of those extra sources -- needing
context is not the same as being unenforceable. Answer false only when no
combination of them could settle it.

An ambiguous term is NOT a reason to answer false: an ambiguity is recorded as a
question for the policy owner in a later stage, and the item is kept.

Return ONLY JSON, with exactly this shape:

{"is_relevant": bool, "can_be_validated": bool, "reason": str}

`reason` is one sentence, and matters most when either answer is false.
"""


def user(ctx: GenContext, tool: ToolInfo, item: dict) -> str:
    return (
        "[STAGE:review]\n"
        "Judge the policy item below against the tool below.\n\n"
        f"{render_tool_detail(tool)}\n\n"
        f"Policy item:\n{json.dumps(item, indent=2)}\n\n"
        "POLICY RULES:\n"
        f"{render_policy_rules(ctx)}\n\n"
        "System variables available (input.extensions.subject.*):\n"
        f"{render_system_vars(ctx)}\n\n"
        "All tools in this agent (any read-only one may supply context):\n"
        f"{render_tools_overview(ctx)}\n\n"
        "Return only the JSON described in the system prompt."
    )
