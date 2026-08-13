"""The shared per-run context every stage renders its prompt slice from.

Each stage needs a different combination of the policy document, the tool
catalog, the current tool's detail, and the system variables. Building them
all once and rendering slices from pure helpers keeps every stage looking at
the same inputs — in v1 the feasibility reviewer was never shown the system
variables it was implicitly judging against.
"""

import json
from typing import List, Sequence

from pydantic import BaseModel, Field

from toolguard.buildtime.gen_spec.data_types import ToolInfo
from toolguard.buildtime.gen_spec_v2.sysvars import (
    SystemVars,
    SystemVarsInput,
    load_system_vars,
    render_system_vars,
)
from toolguard.buildtime.gen_spec_v2.tools_input import TOOLS_V2, to_tool_infos


class GenContext(BaseModel):
    """Everything generation knows, independent of which tool is in hand."""

    policy_text: str
    tools: List[ToolInfo] = Field(default_factory=list)
    system_vars: SystemVars = Field(default_factory=SystemVars)

    @classmethod
    def build(
        cls,
        policy_text: str,
        tools: TOOLS_V2,
        system_vars: SystemVarsInput = None,
    ) -> "GenContext":
        return cls(
            policy_text=policy_text,
            tools=to_tool_infos(tools),
            system_vars=load_system_vars(system_vars),
        )

    def tool_names(self) -> List[str]:
        return [tool.name for tool in self.tools]

    def tool_by_name(self, name: str) -> ToolInfo:
        for tool in self.tools:
            if tool.name == name:
                return tool
        raise KeyError(f"Unknown tool: {name}")

    def render_policy(self) -> str:
        """The document verbatim.

        v2 does not split it into rules, so headings and section order — real
        context for what a rule applies to — reach the model intact, and every
        reference the model quotes is a span of this exact text.
        """
        return self.policy_text

    def render_system_vars(self) -> str:
        return render_system_vars(self.system_vars)

    def render_tools_overview(self) -> str:
        """A compact ``- <name>: <description>`` catalog of every tool."""
        if not self.tools:
            return "(no tools available)"
        return "\n".join(f"- {tool.name}: {tool.description}" for tool in self.tools)

    def render_tool_detail(self, tool: ToolInfo) -> str:
        """The current tool's signature and full parameter detail."""
        params = {
            name: {
                "type": param.type,
                "description": param.description,
                "required": param.required,
            }
            for name, param in tool.parameters.items()
        }
        return (
            f"Tool name: {tool.name}\n"
            f"Tool description: {tool.description}\n"
            f"Tool signature: {tool.signature}\n"
            f"Tool parameters:\n{json.dumps(params, indent=2)}"
        )

    def render_other_tools(self, tool: ToolInfo) -> str:
        """The catalog minus the current tool.

        What a rule can lean on for a prior lookup is exactly the *other*
        tools, so ``requires.tool_history`` is judged against this list.
        """
        others: Sequence[ToolInfo] = [t for t in self.tools if t.name != tool.name]
        if not others:
            return "(no other tools available)"
        return "\n".join(f"- {t.name}: {t.description}" for t in others)
