"""Prompt for the expand stage: find rules the create stage missed."""

from __future__ import annotations

import json
from typing import List

from toolguard.buildtime.gen_spec.data_types import ToolInfo
from toolguard.buildtime.gen_spec_v2.context import (
    GenContext,
    render_policy_rules,
    render_system_vars,
    render_tool_detail,
    render_tools_overview,
)

SYSTEM = """You look for policy rules that a first pass missed for ONE tool.

You are shown the tool, every policy rule, the system variables available, the
other tools in this agent, and the policy items already captured for this tool.
Return ONLY items that are NOT already captured.

The same exclusions as the first pass apply: do not bind a rule that governs a
different tool, an orchestration rule about the agent's own behaviour, a rule
from another domain, a bare permission with nothing to deny, or a definition of
a term rather than a rule.

Return ONLY JSON, with exactly this shape:

{
  "policy_items": [
    {"id": str, "name": str, "description": str, "references": [str, ...]}
  ]
}

Rules for the output:
- `id` MUST be `<tool>.<short_semantic_slug>`, lowercase, underscore-separated,
  and different from every id already captured.
- `references` MUST be a NON-EMPTY list of quotes copied EXACTLY from the POLICY
  RULES section. Do NOT paraphrase.
- Return an empty `policy_items` list when nothing was missed. That is the
  expected answer once the first pass did its job -- do not invent items to fill
  the list.
"""


def user(ctx: GenContext, tool: ToolInfo, captured: List[dict]) -> str:
    return (
        "[STAGE:expand]\n"
        "Return only policy rules governing the tool below that are missing "
        "from the already-captured list.\n\n"
        f"{render_tool_detail(tool)}\n\n"
        "POLICY RULES (quote these verbatim in `references`):\n"
        f"{render_policy_rules(ctx)}\n\n"
        "System variables available (input.extensions.subject.*):\n"
        f"{render_system_vars(ctx)}\n\n"
        "All tools in this agent:\n"
        f"{render_tools_overview(ctx)}\n\n"
        f"Already captured for this tool:\n{json.dumps(captured, indent=2)}\n\n"
        "Return only the JSON described in the system prompt."
    )
