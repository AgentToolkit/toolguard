"""The shared per-run context every stage renders its prompt from.

Each stage needs a different slice of the same three inputs -- the policy rules,
the acting user's variables, and the tool catalog -- so callers build one
:class:`GenContext` per run and stages call the ``render_*`` helpers below. The
helpers are pure: they format, they never call the model.
"""

from __future__ import annotations

import json
from typing import List

from pydantic import BaseModel, Field

from toolguard.buildtime.gen_spec.data_types import ToolInfo
from toolguard.buildtime.gen_spec_v2.inputs import PolicyRule, SystemVars

#: Where a system variable lives at evaluation time. Rendered into every prompt
#: so the model does not mistake a subject variable for a tool argument.
SUBJECT_PATH = "input.extensions.subject"

#: Where a tool argument lives at evaluation time.
ARGUMENTS_PATH = "input.arguments"


class GenContext(BaseModel):
    policy_rules: List[PolicyRule] = Field(default_factory=list)
    system_vars: SystemVars = Field(default_factory=SystemVars)
    tools: List[ToolInfo] = Field(default_factory=list)


def render_policy_rules(ctx: GenContext) -> str:
    """Every rule verbatim, one per line, as ``- <rule>``."""
    if not ctx.policy_rules:
        return "(no policy rules available)"
    return "\n".join(f"- {rule.text}" for rule in ctx.policy_rules)


def render_system_vars(ctx: GenContext) -> str:
    """Each subject variable's name, path, and domain or example value.

    A list-valued entry is an allowed-value enum; a scalar is an example value.
    """
    if not ctx.system_vars.names:
        return "(no system variables available)"

    lines = []
    for name in ctx.system_vars.names:
        value = ctx.system_vars.raw.get(name)
        path = f"{SUBJECT_PATH}.{name}"
        if isinstance(value, list):
            lines.append(f"- {name} ({path}): allowed values = {json.dumps(value)}")
        else:
            lines.append(f"- {name} ({path}): example value = {json.dumps(value)}")
    return "\n".join(lines)


def render_tools_overview(ctx: GenContext) -> str:
    """A compact ``- <name>: <description>`` catalog of every tool in the agent."""
    if not ctx.tools:
        return "(no tools available)"
    return "\n".join(f"- {tool.name}: {tool.description}" for tool in ctx.tools)


def render_tool_detail(tool: ToolInfo) -> str:
    """The current tool in full: description, parameters, and signature.

    The signature carries the return type, which is what a ``post_tool`` rule
    has to reason about -- :class:`ToolInfo` has no separate result schema.
    """
    parameters = {name: param.model_dump() for name, param in tool.parameters.items()}
    return (
        f"Tool name: {tool.name}\n"
        f"Tool description: {tool.description}\n"
        f"Tool signature: {tool.signature}\n"
        f"Tool parameters:\n{json.dumps(parameters, indent=2)}"
    )
