"""Reading and writing v2 spec files in the format's fixed key order.

Pydantic serializes in declaration order and always emits every field, but
the on-disk format fixes both the key order and a set of omit-when-empty
keys. This module owns that mapping in both directions so
:mod:`toolguard.buildtime.gen_spec_v2.models` stays a plain schema.

Output is byte-identical to the ground-truth specs under
``tests/data/specs_v2/``, which is what ``test_serialize.py`` asserts.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from toolguard.buildtime.gen_spec_v2.models import (
    Conflict,
    PendingItem,
    PolicyItemV2,
    Requires,
    ResolvedItem,
    Resolution,
    SpecDebugV2,
    SpecV2,
)


def _requires_to_dict(requires: Requires) -> Dict[str, Any]:
    """All three keys are always present, even when empty or null."""
    return {
        "system_vars": list(requires.system_vars),
        "tool_history": (
            None
            if requires.tool_history is None
            else [
                {"tool": entry.tool, "params": dict(entry.params)}
                for entry in requires.tool_history
            ]
        ),
        "message_history": requires.message_history,
    }


def _resolution_to_dict(resolution: Optional[Resolution]) -> Optional[Dict[str, Any]]:
    if resolution is None:
        return None
    return {
        "answer": resolution.answer,
        "decided_by": resolution.decided_by,
        "effect": resolution.effect,
    }


def _pending_to_dict(pending: PendingItem) -> Dict[str, Any]:
    """``question`` follows the optional suggestions, matching the format."""
    d: Dict[str, Any] = {"type": pending.type.value, "detail": pending.detail}
    if pending.suggested_tool is not None:
        d["suggested_tool"] = pending.suggested_tool
    if pending.suggested_source is not None:
        d["suggested_source"] = pending.suggested_source
    d["question"] = pending.question
    if isinstance(pending, ResolvedItem):
        d["resolution"] = _resolution_to_dict(pending.resolution)
    return d


def _item_to_dict(item: PolicyItemV2) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "compliance_examples": list(item.compliance_examples),
        "violation_examples": list(item.violation_examples),
        "references": list(item.references),
        "trigger": item.trigger.value,
        "requires": _requires_to_dict(item.requires),
    }
    if item.pending_for_user:
        d["pending_for_user"] = [_pending_to_dict(p) for p in item.pending_for_user]
    if item.resolved_by_user:
        d["resolved_by_user"] = [_pending_to_dict(r) for r in item.resolved_by_user]
    return d


def _conflict_to_dict(conflict: Conflict) -> Dict[str, Any]:
    return {
        "id": conflict.id,
        "name": conflict.name,
        "kind": conflict.kind,
        "conflicting_policies": list(conflict.conflicting_policies),
        "description": conflict.description,
        "question": conflict.question,
        "resolution": _resolution_to_dict(conflict.resolution),
    }


def _debug_to_dict(debug: SpecDebugV2) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "tool_info": {
            "is_read_only": debug.tool_info.is_read_only,
            "user_enrichment": debug.tool_info.user_enrichment,
        },
        "archive": list(debug.archive),
    }
    if debug.notes is not None:
        d["notes"] = list(debug.notes)
    return d


def spec_to_dict(spec: SpecV2) -> Dict[str, Any]:
    """Serialize ``spec`` in the fixed on-disk key order.

    Omitted when empty: ``conflicts`` on the spec, ``pending_for_user`` and
    ``resolved_by_user`` on an item, ``suggested_tool`` / ``suggested_source``
    on a pending item, and ``debug.notes``. Everything else is always
    present, even when empty.
    """
    d: Dict[str, Any] = {
        "tool_name": spec.tool_name,
        "source_doc": spec.source_doc,
        "policy_items": [_item_to_dict(item) for item in spec.policy_items],
    }
    if spec.conflicts:
        d["conflicts"] = [_conflict_to_dict(c) for c in spec.conflicts]
    d["debug"] = _debug_to_dict(spec.debug)
    return d


def spec_from_dict(d: Dict[str, Any]) -> SpecV2:
    """Inverse of :func:`spec_to_dict`; missing optional keys default to empty."""
    return SpecV2.model_validate(d)


def dump_spec_str(spec: SpecV2) -> str:
    """Render ``spec`` as the exact text written to disk, trailing newline included."""
    return json.dumps(spec_to_dict(spec), indent=2, ensure_ascii=False) + "\n"


def dump_spec(spec: SpecV2, path: str | Path) -> None:
    Path(path).write_text(dump_spec_str(spec), encoding="utf-8")


def load_spec(path: str | Path) -> SpecV2:
    return spec_from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def load_specs(directory: str | Path, skip: Optional[List[str]] = None) -> List[SpecV2]:
    """Load every ``<tool>.json`` in ``directory``, sorted by filename.

    Files whose stem is in ``skip`` are ignored, as is anything starting with
    ``_`` (e.g. a caller's ``_manifest.json``).
    """
    skipped = set(skip or ())
    specs = []
    for path in sorted(Path(directory).glob("*.json")):
        if path.name.startswith("_") or path.stem in skipped:
            continue
        specs.append(load_spec(path))
    return specs
