"""System prompts and per-stage user-content assembly.

The system prompt for each stage is a ``.txt`` file in this package, matching
toolguard's convention; the user content is assembled here, because each stage
needs a different slice of :class:`GenContext` and assembling it in Python
keeps the slice explicit and testable.

Every stage is shown the system variables and the other tools, whether or not
it obviously needs them: in v1 the feasibility reviewer judged "can this be
validated" without ever being shown the variables that would decide it.
"""

import json
import os
from functools import lru_cache
from typing import Any, Dict, List

from toolguard.buildtime.gen_spec.data_types import ToolInfo
from toolguard.buildtime.gen_spec_v2.context import GenContext

JSON_ONLY_SUFFIX = """
CRITICAL OUTPUT RULES:
- Output MUST be valid JSON.
- Output MUST match the schema exactly.
- Do NOT include explanations, markdown, comments, or extra text.
- Do NOT wrap the JSON in code fences.
- The first character of the response must be '{' and the last must be '}'.
"""

STAGES = ("create", "expand", "review", "enrich", "examples", "conflicts")


@lru_cache(maxsize=None)
def system(stage: str) -> str:
    """The system prompt for ``stage``, with the JSON-only rules appended."""
    if stage not in STAGES:
        raise KeyError(f"Unknown stage: {stage}")
    path = os.path.join(os.path.dirname(__file__), f"{stage}.txt")
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read() + JSON_ONLY_SUFFIX


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)


def _policy_block(ctx: GenContext) -> str:
    return f"POLICY DOCUMENT:\n{ctx.render_policy()}"


def _system_vars_block(ctx: GenContext) -> str:
    return (
        "System variables available (input.extensions.subject.*):\n"
        f"{ctx.render_system_vars()}"
    )


def _all_tools_block(ctx: GenContext) -> str:
    return f"All tools in this agent:\n{ctx.render_tools_overview()}"


def _other_tools_block(ctx: GenContext, tool: ToolInfo) -> str:
    return f"Other tools available for a prior lookup:\n{ctx.render_other_tools(tool)}"


def create_user(ctx: GenContext, tool: ToolInfo) -> str:
    return "\n\n".join(
        [
            "[STAGE:create]",
            "Bind every policy rule that governs or constrains the tool below to it, "
            "including cross-cutting rules instantiated for this tool.",
            ctx.render_tool_detail(tool),
            _policy_block(ctx),
            _system_vars_block(ctx),
            _all_tools_block(ctx),
            "Return only the JSON described in the system prompt.",
        ]
    )


def expand_user(
    ctx: GenContext, tool: ToolInfo, existing_items: List[Dict[str, Any]]
) -> str:
    return "\n\n".join(
        [
            "[STAGE:expand]",
            "Find any additional policy rules applicable to the tool below, beyond "
            "the items already captured.",
            ctx.render_tool_detail(tool),
            _policy_block(ctx),
            _system_vars_block(ctx),
            _all_tools_block(ctx),
            f"Existing policy items for this tool:\n{_json(existing_items)}",
            "Return only the JSON described in the system prompt.",
        ]
    )


def review_user(ctx: GenContext, tool: ToolInfo, item: Dict[str, Any]) -> str:
    return "\n\n".join(
        [
            "[STAGE:review]",
            "Review the policy item below for the given tool.",
            ctx.render_tool_detail(tool),
            _policy_block(ctx),
            _system_vars_block(ctx),
            _other_tools_block(ctx, tool),
            f"Policy item:\n{_json(item)}",
            "Return only the JSON described in the system prompt.",
        ]
    )


def enrich_user(ctx: GenContext, tool: ToolInfo, item: Dict[str, Any]) -> str:
    return "\n\n".join(
        [
            "[STAGE:enrich]",
            "Enrich the policy item below with trigger, requires, validated "
            "references, and any pending_for_user gaps.",
            ctx.render_tool_detail(tool),
            f"{_policy_block(ctx)}\n\n(Validate the item's references against the "
            "document above, verbatim.)",
            f"Policy item:\n{_json(item)}",
            _system_vars_block(ctx),
            _other_tools_block(ctx, tool),
            "Return only the JSON described in the system prompt.",
        ]
    )


def examples_user(ctx: GenContext, tool: ToolInfo, item: Dict[str, Any]) -> str:
    return "\n\n".join(
        [
            "[STAGE:examples]",
            "Write compliance and violation examples for the policy item below, for "
            "the given tool.",
            ctx.render_tool_detail(tool),
            f"Policy item:\n{_json(item)}",
            "System variables available (input.extensions.subject.*) — use realistic "
            f"values from these when writing examples:\n{ctx.render_system_vars()}",
            "Return only the JSON described in the system prompt.",
        ]
    )


def conflicts_user(
    tool_name: str, target: Dict[str, Any], others: List[Dict[str, Any]]
) -> str:
    return "\n\n".join(
        [
            "[STAGE:conflicts]",
            f"Given a TARGET policy item and OTHER policy items from the tool "
            f"`{tool_name}`, identify any conflicts between the TARGET and any of "
            "the OTHERS.",
            f"TARGET:\n{_json(target)}",
            f"OTHERS:\n{_json(others)}",
            "Return only the JSON described in the system prompt.",
        ]
    )
