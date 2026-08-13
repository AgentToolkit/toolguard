"""Combining repeated enrich votes into one answer.

The enrich stage asks the model the same question several times, because a
single answer about "does this rule need the chat history?" is unreliable.
This module reduces those answers to one, with deliberately asymmetric rules:

- **system_vars** unions. A missed variable produces a guard that reads the
  wrong thing; a spurious one only over-declares.
- **message_history** and a null **tool_history** need a strict majority. Both
  make an item unenforceable by today's codegen, so one stray vote must not
  decide it.
- **trigger** ties resolve to ``pre_tool``: a pre-tool guard that should have
  been post-tool blocks a call, while the reverse lets one through.

Votes come from an LLM, so every field is read defensively — a malformed vote
is skipped, never fatal.
"""

from typing import Any, Dict, List, Optional, Sequence

from loguru import logger
from pydantic import BaseModel, Field, ValidationError

from toolguard.buildtime.gen_spec_v2.models import (
    PendingItem,
    Requires,
    ToolHistoryEntry,
    Trigger,
)


class Reconciled(BaseModel):
    """One answer, reduced from many votes."""

    trigger: Trigger = Trigger.pre_tool
    requires: Requires = Field(default_factory=Requires)
    references: List[str] = Field(default_factory=list)
    pending_for_user: List[PendingItem] = Field(default_factory=list)


def _requires_of(vote: Dict[str, Any]) -> Dict[str, Any]:
    requires = vote.get("requires")
    return requires if isinstance(requires, dict) else {}


def _str_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [v for v in value if isinstance(v, str)]


def _tool_history_of(vote: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = _requires_of(vote).get("tool_history")
    if not isinstance(raw, list):
        return []
    return [entry for entry in raw if isinstance(entry, dict) and entry.get("tool")]


def _reconcile_trigger(votes: Sequence[Dict[str, Any]]) -> Trigger:
    post = sum(1 for v in votes if v.get("trigger") == Trigger.post_tool.value)
    pre = sum(1 for v in votes if v.get("trigger") == Trigger.pre_tool.value)
    return Trigger.post_tool if post > pre else Trigger.pre_tool


def _reconcile_tool_history(
    votes: Sequence[Dict[str, Any]],
) -> Optional[List[ToolHistoryEntry]]:
    histories = [_tool_history_of(v) for v in votes]
    empty = sum(1 for h in histories if not h)
    if votes and empty * 2 > len(votes):
        return None

    candidates = [h for h in histories if h]
    if not candidates:
        return None

    longest = max(candidates, key=len)
    entries = []
    for entry in longest:
        params = entry.get("params")
        entries.append(
            ToolHistoryEntry(
                tool=str(entry["tool"]),
                params={
                    str(k): str(v)
                    for k, v in (params.items() if isinstance(params, dict) else [])
                },
            )
        )
    return entries or None


def _reconcile_message_history(votes: Sequence[Dict[str, Any]]) -> Optional[bool]:
    """``True`` on a strict majority, otherwise ``None`` — the format has no false."""
    wanted = sum(1 for v in votes if _requires_of(v).get("message_history") is True)
    return True if votes and wanted * 2 > len(votes) else None


def _reconcile_references(votes: Sequence[Dict[str, Any]]) -> List[str]:
    references: List[str] = []
    for vote in votes:
        for reference in _str_list(vote.get("references")):
            if reference not in references:
                references.append(reference)
    return references


def _reconcile_pending(votes: Sequence[Dict[str, Any]]) -> List[PendingItem]:
    """Dedupe by ``(type, question)``, first occurrence winning.

    An entry that will not validate — unknown type, no question — is dropped:
    a gap nobody can act on is worse than no gap at all.
    """
    pending: List[PendingItem] = []
    seen = set()
    for vote in votes:
        raw_entries = vote.get("pending_for_user")
        if not isinstance(raw_entries, list):
            continue
        for raw in raw_entries:
            if not isinstance(raw, dict):
                continue
            try:
                entry = PendingItem.model_validate(raw)
            except ValidationError as ex:
                logger.warning("Dropping unusable pending entry {}: {}", raw, ex.title)
                continue
            key = (entry.type, entry.question)
            if key in seen:
                continue
            seen.add(key)
            pending.append(entry)
    return pending


def reconcile(votes: Sequence[Any]) -> Reconciled:
    """Reduce ``votes`` to one answer. Non-dict votes are ignored."""
    usable = [v for v in votes if isinstance(v, dict)]

    system_vars = sorted(
        {sv for v in usable for sv in _str_list(_requires_of(v).get("system_vars"))}
    )

    return Reconciled(
        trigger=_reconcile_trigger(usable),
        requires=Requires(
            system_vars=system_vars,
            tool_history=_reconcile_tool_history(usable),
            message_history=_reconcile_message_history(usable),
        ),
        references=_reconcile_references(usable),
        pending_for_user=_reconcile_pending(usable),
    )
