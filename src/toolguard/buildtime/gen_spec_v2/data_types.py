"""Models and on-disk form for the step1 per-tool guard spec.

The JSON these models emit is governed by `step1.schema.json` (vendored into
`tests/buildtime/gen_spec_v2/` from the benchmark repo). Two of its rules drive
every design choice here:

* Some keys must disappear when empty, because the schema gives them
  ``minItems: 1``: ``conflicts``, ``pending_for_user``, ``resolved_by_user``.
* Some keys must survive when empty, because "nothing needed" is spelled as the
  empty or false value and never as ``null``: ``system_vars``, ``tool_history``,
  ``message_history``. A conflict's ``resolution`` is the one key that is
  always an explicit ``null`` -- a conflict exists only while it is pending.

Serialization therefore goes through :meth:`to_dict` rather than pydantic's
``model_dump``: the key order is fixed to the schema's order and the
conditional keys are decided per object. ``model_dump`` output is NOT the
on-disk form; :func:`dump_spec` is.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set

from pydantic import BaseModel, Field

Trigger = Literal["pre_tool", "post_tool"]
QuestionType = Literal["clarification", "missing_variable", "missing_tool"]
ConflictKind = Literal["scope", "definition"]

#: The question type whose companion key is required, per the schema's if/then.
SUGGESTION_KEY: Dict[str, str] = {
    "missing_variable": "suggested_source",
    "missing_tool": "suggested_tool",
}


def slugify(text: str) -> str:
    """Lowercase and collapse every non-alphanumeric run to a single ``_``.

    The result feeds an item id, which the schema constrains to
    ``^[a-z0-9_]+\\.[a-z0-9_]+$`` -- so dots, dashes and capitals must all go.
    """
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def unique_id(tool: str, slug: str, taken: Set[str]) -> str:
    """Return ``<tool>.<slug>``, suffixing ``_2``, ``_3``, ... until unused.

    ``taken`` is read-only; callers add the returned id themselves.
    """
    base = f"{tool}.{slug}"
    if base not in taken:
        return base
    n = 2
    while f"{base}_{n}" in taken:
        n += 1
    return f"{base}_{n}"


class ToolHistoryEntry(BaseModel):
    """A prior read-only tool call whose result a rule depends on."""

    tool: str
    params: Dict[str, str] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"tool": self.tool, "params": dict(self.params)}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ToolHistoryEntry":
        return cls(tool=d["tool"], params=dict(d.get("params") or {}))


class Requires(BaseModel):
    """What a rule needs in order to be evaluated.

    "Nothing needed" is ``[]`` / ``[]`` / ``False`` -- never ``None``.
    """

    system_vars: List[str] = Field(default_factory=list)
    tool_history: List[ToolHistoryEntry] = Field(default_factory=list)
    message_history: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_vars": list(self.system_vars),
            "tool_history": [e.to_dict() for e in self.tool_history],
            "message_history": self.message_history,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Requires":
        return cls(
            system_vars=list(d.get("system_vars") or []),
            tool_history=[
                ToolHistoryEntry.from_dict(e) for e in (d.get("tool_history") or [])
            ],
            message_history=bool(d.get("message_history")),
        )


class Resolution(BaseModel):
    """A decision a human made about a question."""

    answer: str
    decided_by: Literal["human"] = "human"
    effect: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "decided_by": self.decided_by,
            "effect": self.effect,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Resolution":
        return cls(answer=d["answer"], decided_by=d["decided_by"], effect=d["effect"])


class PendingItem(BaseModel):
    """An open question that blocks full enforcement of a rule.

    The schema ties the companion key to ``type``: ``missing_variable`` requires
    ``suggested_source`` and forbids ``suggested_tool``, ``missing_tool`` is the
    mirror image, and ``clarification`` forbids both. Emission enforces that,
    so a mismatched pair on the object cannot reach disk.
    """

    type: QuestionType
    detail: str
    question: str
    suggested_source: Optional[str] = None
    suggested_tool: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"type": self.type, "detail": self.detail}
        key = SUGGESTION_KEY.get(self.type)
        if key is not None:
            value = getattr(self, key)
            if value is not None:
                d[key] = value
        d["question"] = self.question
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PendingItem":
        return cls(
            type=d["type"],
            detail=d["detail"],
            question=d["question"],
            suggested_source=d.get("suggested_source"),
            suggested_tool=d.get("suggested_tool"),
        )


class ResolvedItem(PendingItem):
    """A question that was raised and answered; the answer is baked into the rule."""

    resolution: Resolution

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["resolution"] = self.resolution.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ResolvedItem":
        return cls(
            type=d["type"],
            detail=d["detail"],
            question=d["question"],
            suggested_source=d.get("suggested_source"),
            suggested_tool=d.get("suggested_tool"),
            resolution=Resolution.from_dict(d["resolution"]),
        )


class PolicyItemV2(BaseModel):
    """One active guard rule."""

    id: str
    name: str
    description: str
    compliance_examples: List[str] = Field(default_factory=list)
    violation_examples: List[str] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list)
    trigger: Trigger = "pre_tool"
    requires: Requires = Field(default_factory=Requires)
    pending_for_user: List[PendingItem] = Field(default_factory=list)
    resolved_by_user: List[ResolvedItem] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "compliance_examples": list(self.compliance_examples),
            "violation_examples": list(self.violation_examples),
            "references": list(self.references),
            "trigger": self.trigger,
            "requires": self.requires.to_dict(),
        }
        if self.pending_for_user:
            d["pending_for_user"] = [p.to_dict() for p in self.pending_for_user]
        if self.resolved_by_user:
            d["resolved_by_user"] = [r.to_dict() for r in self.resolved_by_user]
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PolicyItemV2":
        return cls(
            id=d["id"],
            name=d["name"],
            description=d["description"],
            compliance_examples=list(d.get("compliance_examples") or []),
            violation_examples=list(d.get("violation_examples") or []),
            references=list(d.get("references") or []),
            trigger=d.get("trigger") or "pre_tool",
            requires=Requires.from_dict(d.get("requires") or {}),
            pending_for_user=[
                PendingItem.from_dict(p) for p in (d.get("pending_for_user") or [])
            ],
            resolved_by_user=[
                ResolvedItem.from_dict(r) for r in (d.get("resolved_by_user") or [])
            ],
        )


class Conflict(BaseModel):
    """An open interaction between two or more of one tool's policy items.

    ``resolution`` is always ``None``: the entry exists only while the question
    is unanswered. Once decided, the conflict is removed and the decision is
    recorded as a :class:`ResolvedItem` on the affected policy items.
    """

    id: str
    name: str
    kind: ConflictKind
    conflicting_policies: List[str]
    description: str
    question: str
    resolution: None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "conflicting_policies": list(self.conflicting_policies),
            "description": self.description,
            "question": self.question,
            "resolution": None,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Conflict":
        return cls(
            id=d["id"],
            name=d["name"],
            kind=d["kind"],
            conflicting_policies=list(d["conflicting_policies"]),
            description=d["description"],
            question=d["question"],
        )


class ToolGuardSpecV2(BaseModel):
    """One tool's guard spec -- the content of a single ``<tool_name>.json``."""

    tool_name: str
    source_doc: str
    policy_items: List[PolicyItemV2] = Field(default_factory=list)
    conflicts: List[Conflict] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "tool_name": self.tool_name,
            "source_doc": self.source_doc,
            "policy_items": [item.to_dict() for item in self.policy_items],
        }
        if self.conflicts:
            d["conflicts"] = [c.to_dict() for c in self.conflicts]
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ToolGuardSpecV2":
        return cls(
            tool_name=d["tool_name"],
            source_doc=d["source_doc"],
            policy_items=[
                PolicyItemV2.from_dict(item) for item in (d.get("policy_items") or [])
            ],
            conflicts=[Conflict.from_dict(c) for c in (d.get("conflicts") or [])],
        )


class RejectedItem(BaseModel):
    """An item that was generated and then dropped, with why and by which stage.

    A run artifact, NOT spec content: a spec carries only enforceable rules, so
    the schema has no place for this. It is reported to the caller and written
    beside the specs so "why did this tool get no rule for that line?" stays
    answerable after the run.
    """

    item: PolicyItemV2
    reason: str
    stage: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item": self.item.to_dict(),
            "reason": self.reason,
            "stage": self.stage,
        }


def load_spec(path: str | Path) -> ToolGuardSpecV2:
    return ToolGuardSpecV2.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def dump_spec(spec: ToolGuardSpecV2, path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(spec.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
