"""The v2 guard-spec schema.

These models describe the on-disk JSON that ``gen_spec_v2`` produces: the
v1 spec (``toolguard.runtime.data_types.ToolGuardSpec``) plus everything
needed to say *who* is acting, *when* a rule applies, *what else* is needed
to decide it, and *what is missing* to enforce it at all.

They are buildtime-only. The runtime and the code generator consume v1
specs; :mod:`toolguard.buildtime.gen_spec_v2.adapter` is the bridge.

Serialization lives in :mod:`toolguard.buildtime.gen_spec_v2.serialize`, not
here: the on-disk key order is fixed by the format and differs from these
classes' declaration order.
"""

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from toolguard.buildtime.compat.strenum import StrEnum


def slugify(text: str) -> str:
    """Lowercase, collapse non-alphanumeric runs to a single ``_``, strip edges."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def unique_id(tool: str, slug: str, taken: set) -> str:
    """Return ``f"{tool}.{slug}"``, suffixing ``_2``, ``_3``, ... until unused.

    ``taken`` is read-only; it is never mutated here.
    """
    base = f"{tool}.{slug}"
    if base not in taken:
        return base
    n = 2
    while f"{base}_{n}" in taken:
        n += 1
    return f"{base}_{n}"


class Trigger(StrEnum):
    """When a policy item is evaluated."""

    pre_tool = "pre_tool"
    """Before the tool is invoked, against its arguments."""

    post_tool = "post_tool"
    """After the tool returns, against its result."""


class PendingType(StrEnum):
    """Why a policy item cannot be enforced without a human's input."""

    missing_tool = "missing_tool"
    """The rule needs a tool that the tool set does not expose."""

    missing_var = "missing_var"
    """The rule needs a subject variable that ``system_vars`` does not supply."""

    clarification = "clarification"
    """The rule is ambiguous; only a human can pick the deterministic reading."""

    @classmethod
    def _missing_(cls, value: object) -> Optional["PendingType"]:
        """Accept known spellings that drift out of generation.

        ``missing_variable`` appears in specs generated before the vocabulary
        was an enum, and is silently ignored by any code matching on
        ``missing_var``. Normalize instead of rejecting, so old specs load.
        """
        # Dict[str, Any], not Dict[str, PendingType]: the StrEnum compat shim
        # makes mypy read a member accessed via `cls` as a plain `str`.
        aliases: Dict[str, Any] = {
            "missing_variable": cls.missing_var,
            "missing_system_var": cls.missing_var,
            "missing_tools": cls.missing_tool,
        }
        if isinstance(value, str):
            return aliases.get(value.strip().lower())
        return None


class ToolHistoryEntry(BaseModel):
    """A tool that must be called, and with which arguments, before deciding."""

    tool: str
    params: Dict[str, str] = Field(
        default_factory=dict,
        description="Param name -> expression for its value, e.g. 'input.arguments.user_id'",
    )


class Requires(BaseModel):
    """What a policy item needs in order to be decided."""

    system_vars: List[str] = Field(
        default_factory=list,
        description="Subject-variable names the item reads, e.g. ['user_id', 'department']",
    )
    tool_history: Optional[List[ToolHistoryEntry]] = Field(
        default=None,
        description="Tool calls whose results the item needs; None when it needs none",
    )
    message_history: Optional[bool] = Field(
        default=None,
        description="True when the item can only be decided from the conversation",
    )


class PendingItem(BaseModel):
    """A gap a human must close before the item can be enforced."""

    type: PendingType
    detail: str = Field(..., description="What is missing, and why it blocks the item")
    question: str = Field(..., description="The question to put to the user")
    suggested_tool: Optional[str] = None
    suggested_source: Optional[str] = None


class Resolution(BaseModel):
    """A human's answer to a pending item or a conflict."""

    answer: str
    decided_by: str
    effect: str = Field(..., description="What changed in the spec as a result")


class ResolvedItem(PendingItem):
    """A :class:`PendingItem` a human has already answered."""

    resolution: Resolution


class PolicyItemV2(BaseModel):
    """One enforceable rule, attached to one tool."""

    id: str = Field(..., description="Stable '<tool>.<slug>' identifier")
    name: str
    description: str
    compliance_examples: List[str] = Field(default_factory=list)
    violation_examples: List[str] = Field(default_factory=list)
    references: List[str] = Field(
        default_factory=list, description="Verbatim spans of the policy document"
    )
    trigger: Trigger = Field(default=Trigger.pre_tool)
    requires: Requires = Field(default_factory=Requires)
    pending_for_user: List[PendingItem] = Field(default_factory=list)
    resolved_by_user: List[ResolvedItem] = Field(default_factory=list)


class Conflict(BaseModel):
    """Two or more policy items that disagree, and the question that settles it."""

    id: str
    name: str
    kind: str = Field(..., description="e.g. 'scope', 'definition', 'dominance'")
    conflicting_policies: List[str] = Field(
        default_factory=list, description="Policy item ids"
    )
    description: str
    question: str
    resolution: Optional[Resolution] = None


class SpecToolInfo(BaseModel):
    """What generation learned about the tool itself.

    Named to avoid colliding with ``gen_spec.data_types.ToolInfo`` (a tool
    signature, a different concept). Still serializes under ``tool_info``.
    """

    is_read_only: bool = False
    user_enrichment: str = ""


class SpecDebugV2(BaseModel):
    """Generation byproducts. Never read by codegen or the runtime."""

    tool_info: SpecToolInfo = Field(default_factory=SpecToolInfo)
    archive: List[Dict[str, Any]] = Field(
        default_factory=list, description="Items dropped by a stage, with the reason"
    )
    notes: Optional[List[Any]] = Field(
        default=None,
        description="Presence-tracked: None means the key is absent on disk",
    )


class SpecV2(BaseModel):
    """Every policy item attached to one tool, plus its conflicts."""

    tool_name: str
    source_doc: str = ""
    policy_items: List[PolicyItemV2] = Field(default_factory=list)
    conflicts: List[Conflict] = Field(default_factory=list)
    debug: SpecDebugV2 = Field(default_factory=SpecDebugV2)

    def item_ids(self) -> set:
        return {item.id for item in self.policy_items}
