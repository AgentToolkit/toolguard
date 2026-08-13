"""Converting v2 specs into the v1 specs that codegen consumes.

``gen_py`` and the runtime speak v1. This module is the only bridge, and its
whole job is honesty about what today's pipeline can enforce: a generated
guard receives ``args`` and ``api`` — no acting user, no chat history — and
the runtime has no post-invocation hook. An item depending on any of those
is marked ``skip`` so codegen leaves it alone, rather than emitting a guard
that checks the wrong thing.

Each condition in :func:`is_enforceable_today` drops out as the runtime gains
the corresponding capability.
"""

from typing import Iterable, List, Optional

from loguru import logger

from toolguard.buildtime.gen_spec_v2.models import PolicyItemV2, SpecV2, Trigger
from toolguard.buildtime.utils import py
from toolguard.runtime.data_types import ToolGuardSpec, ToolGuardSpecItem


def is_enforceable_today(item: PolicyItemV2) -> bool:
    """Whether v1 codegen can generate a correct guard for ``item``.

    False when the item needs the acting user's identity, the conversation,
    evaluation after the call, or an answer from a human. ``tool_history``
    alone is fine: generated guards already get an ``api`` handle.
    """
    return not (
        item.pending_for_user
        or item.requires.message_history
        or item.trigger == Trigger.post_tool
        or item.requires.system_vars
    )


def _unenforceable_reason(item: PolicyItemV2) -> str:
    if item.pending_for_user:
        types = ", ".join(sorted({p.type.value for p in item.pending_for_user}))
        return f"pending_for_user ({types})"
    if item.requires.message_history:
        return "requires message history"
    if item.trigger == Trigger.post_tool:
        return "post_tool trigger"
    return f"requires system vars ({', '.join(item.requires.system_vars)})"


def _module_key(name: str) -> str:
    """The generated module name ``gen_py`` would derive from ``name``.

    Collisions have to be judged here, not on the raw name: codegen rewrites
    ``.`` to ``_`` and then snake-cases, so "rule v1.0" and "rule v1_0" are
    distinct names that would land in the same file.
    """
    return py.to_py_module_name(f"guard_{name.replace('.', '_')}")


def _unique_names(items: Iterable[PolicyItemV2]) -> List[str]:
    """Item names, disambiguated so each maps to its own generated file.

    ``gen_py`` derives a module, a guard function, and a test file from
    ``item.name``. Ids are unique but names are not, so a name that would
    collide gains the distinguishing part of its id. The suffix is appended
    with a space and no punctuation, because snake-casing leaves punctuation
    in place and would produce an invalid identifier.
    """
    names: List[str] = []
    used_keys = set()
    for item in items:
        name = item.name
        if _module_key(name) in used_keys:
            suffix = item.id.split(".", 1)[-1]
            name = f"{item.name} {suffix}"
            n = 2
            while _module_key(name) in used_keys:
                name = f"{item.name} {suffix} {n}"
                n += 1
        names.append(name)
        used_keys.add(_module_key(name))
    return names


def spec_v2_to_v1(spec: SpecV2) -> ToolGuardSpec:
    """Convert one v2 spec, deriving ``skip`` and preserving v2 fields in ``debug``."""
    names = _unique_names(spec.policy_items)
    items = []

    for item, name in zip(spec.policy_items, names):
        enforceable = is_enforceable_today(item)
        if not enforceable:
            logger.debug(
                "{}: skipped for codegen — {}", item.id, _unenforceable_reason(item)
            )
        items.append(
            ToolGuardSpecItem(
                name=name,
                description=item.description,
                references=list(item.references),
                compliance_examples=list(item.compliance_examples),
                violation_examples=list(item.violation_examples),
                skip=not enforceable,
                debug={
                    "id": item.id,
                    "trigger": item.trigger.value,
                    "requires": item.requires.model_dump(),
                    **(
                        {"skip_reason": _unenforceable_reason(item)}
                        if not enforceable
                        else {}
                    ),
                },
            )
        )

    return ToolGuardSpec(
        tool_name=spec.tool_name,
        policy_items=items,
        debug={
            "source_doc": spec.source_doc,
            "tool_info": spec.debug.tool_info.model_dump(),
            "archive": list(spec.debug.archive),
            "conflicts": [c.model_dump() for c in spec.conflicts],
        },
    )


def specs_v2_to_v1(
    specs: Iterable[SpecV2], known_tools: Optional[Iterable[str]] = None
) -> List[ToolGuardSpec]:
    """Convert many specs, optionally dropping those for tools that don't exist.

    Passing ``known_tools`` guards against handing codegen a spec whose
    ``tool_name`` has no tool behind it, which would try to generate a guard
    for nothing.
    """
    allowed = set(known_tools) if known_tools is not None else None
    converted = []
    for spec in specs:
        if allowed is not None and spec.tool_name not in allowed:
            logger.warning(
                "Dropping spec '{}': no such tool in the supplied tool set",
                spec.tool_name,
            )
            continue
        converted.append(spec_v2_to_v1(spec))
    return converted
