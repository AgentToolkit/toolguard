"""Prompt for the enrich stage: trigger, requires, reference check, open questions."""

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

SYSTEM = """You state what ONE policy item needs in order to be enforced.

Output four things.

`trigger`: `pre_tool` when the rule is decided before the call and can deny it;
`post_tool` when it is about the call's result or a required side effect after
it.

`requires`: the context a guard needs.
- `system_vars`: names of the acting user's variables the rule reads. Use ONLY
  names from the list below. "Nothing needed" is `[]`.
- `tool_history`: prior READ-ONLY tool calls whose results the rule depends on,
  each `{"tool": <name from the catalog>, "params": {<param>: <expression>}}`.
  Every expression must be `input.arguments.<field>` (an argument of the guarded
  call), `input.extensions.subject.<name>` (a system variable), or a function
  over one of those, e.g. `year-of(input.arguments.start_date)`. "Nothing
  needed" is `[]`.
- `message_history`: `true` when the rule must inspect the conversation, e.g. to
  find an explicit user confirmation. Otherwise `false`.

NEVER use null in `requires`. "Nothing needed" is `[]` or `false`.

`references`: the item already has references, shown in its JSON. VALIDATE them,
do not choose new ones. Return the subset that appear EXACTLY --
character-for-character -- in the POLICY RULES section. Drop any that do not.
Return `[]` if none do. Do NOT add a reference that was not already there.

`pending_for_user`: what the rule needs that is not available. Each entry is
`{"type": ..., "detail": ..., "question": ...}` plus exactly one companion key:
- `"missing_variable"` -- a needed signal is not among the system variables.
  MUST include `"suggested_source"`.
- `"missing_tool"` -- a needed tool does not exist in the catalog. MUST include
  `"suggested_tool"` naming the single tool that would need to exist.
- `"clarification"` -- the policy text is ambiguous. MUST include NEITHER
  companion key.
Return `[]` when nothing is missing.

Return ONLY JSON, with exactly this shape:

{
  "trigger": "pre_tool" | "post_tool",
  "requires": {
    "system_vars": [str, ...],
    "tool_history": [{"tool": str, "params": {}}],
    "message_history": true | false
  },
  "references": [str, ...],
  "pending_for_user": [{"type": str, "detail": str, "question": str}]
}
"""


def user(ctx: GenContext, tool: ToolInfo, item: dict) -> str:
    return (
        "[STAGE:enrich]\n"
        "State the trigger, the required context, the validated references, and "
        "any open questions for the policy item below.\n\n"
        f"{render_tool_detail(tool)}\n\n"
        f"Policy item:\n{json.dumps(item, indent=2)}\n\n"
        "POLICY RULES (validate the item's references against these, verbatim):\n"
        f"{render_policy_rules(ctx)}\n\n"
        "System variables available (input.extensions.subject.*) -- use only these names:\n"
        f"{render_system_vars(ctx)}\n\n"
        "All tools in this agent (tool_history may name only these):\n"
        f"{render_tools_overview(ctx)}\n\n"
        "Return only the JSON described in the system prompt."
    )
