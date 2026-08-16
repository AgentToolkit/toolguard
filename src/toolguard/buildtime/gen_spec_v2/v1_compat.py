"""Handing v2 specs to the v1 code generator without inventing a second format.

A v2 spec file already loads as a v1 :class:`ToolGuardSpec`: pydantic ignores the
keys v1 does not declare (``id``, ``trigger``, ``requires``, ``source_doc``,
``conflicts``, ``pending_for_user``, ``resolved_by_user``). The single thing v1
needs that v2 does not carry is ``skip`` -- the flag ``gen_py`` uses to leave a
rule out of code generation:

    policy_items=[i for i in spec.policy_items if not i.skip]

So there is no conversion step on disk and no v1 copy of the specs. ``skip`` is
computed here, in memory, at the moment the specs are handed over, and the v2
fields that informed the decision ride along in the item's free-form ``debug``
so a skipped rule can be explained later.

Deliberately NOT written into the spec files: the same field name is read by the
reference evaluator as "do not score this item", which is a different question
from "do not generate code for this". Keeping it out of the files leaves the
scoring meaning to whoever runs the evaluation.
"""

from __future__ import annotations

from typing import List, Sequence

from toolguard.buildtime.gen_spec_v2.data_types import PolicyItemV2, ToolGuardSpecV2
from toolguard.runtime.data_types import ToolGuardSpec, ToolGuardSpecItem


def skip_reasons(item: PolicyItemV2) -> List[str]:
    """Why generated guard code could not enforce ``item``, if it could not.

    Each reason names something the guard would have to read that a generated
    python guard has no access to:

    - ``post_tool`` -- the rule judges the result, not the arguments.
    - ``message_history`` -- it needs the conversation.
    - ``pending`` -- an open question means the intended behaviour is not settled.
    - ``system_vars`` -- it needs the acting user's variables.

    ``tool_history`` is absent by design: generated guards may call the
    application's read-only APIs, so a dependency on a prior read is fine.
    """
    reasons: List[str] = []
    if item.trigger != "pre_tool":
        reasons.append("post_tool")
    if item.requires.message_history:
        reasons.append("message_history")
    if item.pending_for_user:
        reasons.append("pending")
    if item.requires.system_vars:
        reasons.append("system_vars")
    return reasons


def skip_for(item: PolicyItemV2) -> bool:
    """Whether ``gen_py`` should leave this rule out of code generation."""
    return bool(skip_reasons(item))


def _to_v1_item(item: PolicyItemV2) -> ToolGuardSpecItem:
    reasons = skip_reasons(item)
    return ToolGuardSpecItem(
        name=item.name,
        description=item.description,
        references=list(item.references),
        compliance_examples=list(item.compliance_examples),
        violation_examples=list(item.violation_examples),
        skip=bool(reasons),
        debug={
            "v2": {
                "id": item.id,
                "trigger": item.trigger,
                "requires": item.requires.to_dict(),
                "pending_for_user": [p.to_dict() for p in item.pending_for_user],
                "skip_reasons": reasons,
            }
        },
    )


def to_v1_spec(spec: ToolGuardSpecV2) -> ToolGuardSpec:
    """A v1 view of one v2 spec, with ``skip`` computed. Leaves ``spec`` untouched."""
    return ToolGuardSpec(
        tool_name=spec.tool_name,
        policy_items=[_to_v1_item(item) for item in spec.policy_items],
        debug={"source_doc": spec.source_doc},
    )


def to_v1_specs(specs: Sequence[ToolGuardSpecV2]) -> List[ToolGuardSpec]:
    """A v1 view of a whole run, in the order given."""
    return [to_v1_spec(spec) for spec in specs]
