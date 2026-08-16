"""Prompt for the create stage: bind the policy document's rules to one tool."""

from __future__ import annotations

from toolguard.buildtime.gen_spec.data_types import ToolInfo
from toolguard.buildtime.gen_spec_v2.context import (
    GenContext,
    render_policy_rules,
    render_system_vars,
    render_tool_detail,
    render_tools_overview,
)

SYSTEM = """You bind natural-language policy rules to ONE tool.

Given the tool's name, description, parameters and signature, the full list of
policy rules, the system variables available at policy-evaluation time, and a
catalog of every other tool in this agent, decide which rules GOVERN or
CONSTRAIN this tool's invocation or its result.

Bind every rule that applies, INCLUDING cross-cutting rules instantiated
per-tool: a rule that applies to a whole class of tools (e.g. "confirm with the
user before any write operation" applies to every write tool; "HR may view and
edit all employees' data" applies to every employee-data tool) still governs
THIS tool if this tool is a member of that class, and must be bound to it just
like a rule naming this tool specifically.

Do NOT bind:
- a rule that governs a different tool;
- an orchestration rule about the agent's own behaviour rather than about a tool
  call's arguments or result;
- a rule from a different application domain;
- a bare permission with nothing to deny (e.g. "anyone may view X");
- a definition of a term rather than a rule (definitions belong INSIDE the
  descriptions of the rules that use them, spelled out).

A rule is enforceable here when it can be validated using this tool's arguments
or result, the available system variables (which map to
`input.extensions.subject.*`, NOT to tool parameters), or the result of a prior
read-only tool call.

Return ONLY JSON, with exactly this shape:

{
  "tool_info": {"is_read_only": bool, "user_enrichment": str},
  "policy_items": [
    {"id": str, "name": str, "description": str, "references": [str, ...]}
  ]
}

Rules for the output:
- `id` MUST be `<tool>.<short_semantic_slug>`, lowercase, words separated by
  underscores.
- `name` is a one-line human-readable title.
- `description` states the rule so it can be enforced: the deny condition, and
  any case where it does not apply. Spell out every term the rule depends on
  (who counts as HR, what "own data" means) instead of naming it.
- `references` MUST be a NON-EMPTY list of quotes copied EXACTLY --
  character-for-character, including markdown emphasis and backticks -- from the
  POLICY RULES section below. Do NOT paraphrase, summarize, or reword.
- Do NOT emit a policy item you cannot ground in at least one verbatim quote.
- Return an empty `policy_items` list if no rule governs this tool.
"""


def user(ctx: GenContext, tool: ToolInfo) -> str:
    return (
        "[STAGE:create]\n"
        "Bind every policy rule that governs or constrains the tool below to "
        "it, including cross-cutting rules instantiated for this tool.\n\n"
        f"{render_tool_detail(tool)}\n\n"
        "POLICY RULES (quote these verbatim in `references`):\n"
        f"{render_policy_rules(ctx)}\n\n"
        "System variables available (input.extensions.subject.*):\n"
        f"{render_system_vars(ctx)}\n\n"
        "All tools in this agent:\n"
        f"{render_tools_overview(ctx)}\n\n"
        "Return only the JSON described in the system prompt."
    )
