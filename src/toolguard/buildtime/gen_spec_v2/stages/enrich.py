"""The enrich stage: decide a rule's trigger, what it needs, and what is missing.

Several independent votes each propose a ``trigger`` / ``requires`` /
``references`` / ``pending_for_user`` payload; :func:`reconcile` folds them into
one answer with pure logic, and :func:`normalize_pending` forces the open
questions into the shape the spec schema allows.

Reconciliation is deliberately asymmetric about references: a vote may only
confirm or drop the references an item already carries, never add one. Adding is
how a model invents a quote that appears nowhere in the policy document.
"""

from __future__ import annotations

import asyncio
from typing import Any, Collection, Dict, List, Optional, Sequence

from loguru import logger

from toolguard.buildtime.gen_spec.data_types import ToolInfo
from toolguard.buildtime.gen_spec_v2.context import GenContext
from toolguard.buildtime.gen_spec_v2.data_types import (
    SUGGESTION_KEY,
    PendingItem,
    PolicyItemV2,
    Requires,
    ToolHistoryEntry,
)
from toolguard.buildtime.gen_spec_v2.prompts import enrich as enrich_prompt
from toolguard.buildtime.gen_spec_v2.utils import ask_json
from toolguard.buildtime.llm import I_TG_LLM

TRIGGERS = ("pre_tool", "post_tool")


def _requires_of(vote: Dict[str, Any]) -> Dict[str, Any]:
    requires = vote.get("requires")
    return requires if isinstance(requires, dict) else {}


def reconcile(votes: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Fold enrich votes into a single ``trigger`` / ``requires`` / ... answer.

    - ``trigger``: majority of the two legal values; a tie -- including no
      recognizable vote at all -- resolves to ``pre_tool``, the safe default of
      checking before the call happens.
    - ``requires.system_vars``: the sorted union across votes.
    - ``requires.tool_history``: the longest vote's list, unless a strict
      majority of votes say none is needed.
    - ``requires.message_history``: ``True`` only on a strict majority.
    - ``references``: the union across votes in first-seen order. The caller
      intersects this against what the item already had.
    - ``pending_for_user``: every vote's entries, deduped by
      ``(type, question)``, first occurrence winning. Still raw dicts --
      :func:`normalize_pending` turns them into models.

    "Nothing needed" is always the empty or false value: the schema forbids
    nulls inside ``requires``.
    """
    n = len(votes)

    counts = {
        trigger: sum(1 for vote in votes if vote.get("trigger") == trigger)
        for trigger in TRIGGERS
    }
    trigger = "post_tool" if counts["post_tool"] > counts["pre_tool"] else "pre_tool"

    system_vars = sorted(
        {
            name
            for vote in votes
            for name in (_requires_of(vote).get("system_vars") or [])
        }
    )

    histories = [_requires_of(vote).get("tool_history") or [] for vote in votes]
    empty_history_votes = sum(1 for history in histories if not history)
    if n and empty_history_votes * 2 > n:
        tool_history: List[Any] = []
    else:
        candidates = [history for history in histories if history]
        tool_history = max(candidates, key=len) if candidates else []

    wants_messages = sum(
        1 for vote in votes if _requires_of(vote).get("message_history")
    )
    message_history = bool(n and wants_messages * 2 > n)

    references: List[str] = []
    for vote in votes:
        for reference in vote.get("references") or []:
            if reference not in references:
                references.append(reference)

    pending: List[Dict[str, Any]] = []
    seen: set = set()
    for vote in votes:
        for entry in vote.get("pending_for_user") or []:
            if not isinstance(entry, dict):
                continue
            key = (entry.get("type"), entry.get("question"))
            if key in seen:
                continue
            seen.add(key)
            pending.append(entry)

    return {
        "trigger": trigger,
        "requires": {
            "system_vars": system_vars,
            "tool_history": tool_history,
            "message_history": message_history,
        },
        "references": references,
        "pending_for_user": pending,
    }


def normalize_pending(entries: Sequence[Any]) -> List[PendingItem]:
    """Force raw pending entries into the shape the schema permits.

    The schema ties the companion key to the type: ``missing_variable`` requires
    ``suggested_source``, ``missing_tool`` requires ``suggested_tool``, and
    ``clarification`` forbids both. An entry whose companion key is missing is
    downgraded to ``clarification`` -- the generator cannot invent a tool name or
    a data source it was not given, and a downgraded question still reaches the
    policy owner. A companion key the type forbids is stripped.

    Entries that are not dicts, name an unknown type, or lack ``type`` /
    ``detail`` / ``question`` are dropped.
    """
    normalized: List[PendingItem] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        kind = entry.get("type")
        detail = entry.get("detail")
        question = entry.get("question")
        if not kind or not detail or not question:
            continue
        if kind not in ("clarification", *SUGGESTION_KEY):
            logger.warning(f"Dropping pending entry of unknown type {kind!r}")
            continue

        required_key = SUGGESTION_KEY.get(kind)
        suggestion = entry.get(required_key) if required_key else None
        if required_key and not suggestion:
            logger.debug(
                f"Downgrading {kind!r} pending entry with no {required_key} "
                "to 'clarification'"
            )
            kind, required_key, suggestion = "clarification", None, None

        normalized.append(
            PendingItem(
                type=kind,
                detail=detail,
                question=question,
                suggested_source=suggestion
                if required_key == "suggested_source"
                else None,
                suggested_tool=suggestion if required_key == "suggested_tool" else None,
            )
        )
    return normalized


async def _enrich_item(
    llm: I_TG_LLM,
    ctx: GenContext,
    tool: ToolInfo,
    item: PolicyItemV2,
    n_votes: int,
) -> Dict[str, Any]:
    payload = {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "references": list(item.references),
    }
    votes = await asyncio.gather(
        *[
            ask_json(llm, enrich_prompt.SYSTEM, enrich_prompt.user(ctx, tool, payload))
            for _ in range(n_votes)
        ]
    )
    return reconcile(list(votes))


async def run_enrich(
    llm: I_TG_LLM,
    ctx: GenContext,
    tool: ToolInfo,
    items: Sequence[PolicyItemV2],
    n_votes: int,
    declared_system_vars: Optional[Collection[str]] = None,
) -> None:
    """Write each item's reconciled trigger, requires, references and questions.

    References are intersected with what the item already carried: this stage may
    confirm or drop a quote, never introduce one. When validation drops
    everything, the original references are kept instead -- one flaky vote must
    not blank out a grounded quote and turn the item into an unwritable one.

    System variables are filtered to those the run actually declares, and
    tool_history to tools that actually exist, because a spec naming either an
    undeclared variable or an unknown tool is rejected downstream -- and a
    dependency on a tool nobody can call could never be evaluated anyway. The
    right way to record such a gap is a ``missing_tool`` / ``missing_variable``
    question, which the same vote is asked for separately.
    """
    known_tools = {catalog_tool.name for catalog_tool in ctx.tools}
    answers = await asyncio.gather(
        *[_enrich_item(llm, ctx, tool, item, n_votes) for item in items]
    )

    for item, answer in zip(items, answers):
        requires = answer["requires"]
        system_vars = list(requires["system_vars"])
        if declared_system_vars is not None:
            kept_vars = [name for name in system_vars if name in declared_system_vars]
            for dropped in set(system_vars) - set(kept_vars):
                logger.warning(
                    f"{item.id}: dropping undeclared system variable {dropped!r}"
                )
            system_vars = kept_vars

        tool_history: List[ToolHistoryEntry] = []
        for entry in requires["tool_history"]:
            if not isinstance(entry, dict) or not entry.get("tool"):
                continue
            if known_tools and entry["tool"] not in known_tools:
                logger.warning(
                    f"{item.id}: dropping tool_history dependency on unknown tool "
                    f"{entry['tool']!r}"
                )
                continue
            tool_history.append(
                ToolHistoryEntry(
                    tool=entry["tool"], params=dict(entry.get("params") or {})
                )
            )

        original = list(item.references)
        validated = [ref for ref in answer["references"] if ref in original]

        item.trigger = answer["trigger"]
        item.requires = Requires(
            system_vars=system_vars,
            tool_history=tool_history,
            message_history=requires["message_history"],
        )
        item.references = validated or original
        item.pending_for_user = normalize_pending(answer["pending_for_user"])
