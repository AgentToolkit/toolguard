"""Guard-spec generation, v2.

A second, parallel spec generator. Where v1 emits a rule's text and examples,
v2 also records who is acting (``requires.system_vars``), when the rule applies
(``trigger``), what else is needed to decide it (``requires.tool_history``,
``requires.message_history``), and what is missing to enforce it at all
(``pending_for_user``).

Lives beside ``gen_spec`` (v1), which is unchanged and remains the default. The
code generator and runtime still speak v1; :func:`spec_v2_to_v1` is the bridge.

Typical use::

    specs = await generate_guard_specs_v2_full(
        policy_text, tools, llm, work_dir,
        system_vars="sys_var.json", source_doc="policy.md",
    )
    v1_specs = specs_v2_to_v1(specs, known_tools=[t.name for t in tools])
"""

from toolguard.buildtime.gen_spec_v2.adapter import (
    is_enforceable_today,
    spec_v2_to_v1,
    specs_v2_to_v1,
)
from toolguard.buildtime.gen_spec_v2.models import (
    Conflict,
    PendingItem,
    PendingType,
    PolicyItemV2,
    Requires,
    Resolution,
    ResolvedItem,
    SpecDebugV2,
    SpecToolInfo,
    SpecV2,
    ToolHistoryEntry,
    Trigger,
)
from toolguard.buildtime.gen_spec_v2.pipeline import (
    SpecV2Options,
    generate_guard_examples_v2,
    generate_guard_specs_v2,
    generate_guard_specs_v2_full,
    generate_spec_conflicts_v2,
)
from toolguard.buildtime.gen_spec_v2.serialize import (
    dump_spec,
    load_spec,
    load_specs,
    spec_from_dict,
    spec_to_dict,
)

__all__ = [
    # entry points
    "generate_guard_specs_v2",
    "generate_spec_conflicts_v2",
    "generate_guard_specs_v2_full",
    "generate_guard_examples_v2",
    "SpecV2Options",
    # adapter to what codegen and the runtime consume
    "spec_v2_to_v1",
    "specs_v2_to_v1",
    "is_enforceable_today",
    # schema
    "SpecV2",
    "PolicyItemV2",
    "Requires",
    "ToolHistoryEntry",
    "PendingItem",
    "PendingType",
    "Resolution",
    "ResolvedItem",
    "Conflict",
    "SpecToolInfo",
    "SpecDebugV2",
    "Trigger",
    # serialization
    "load_spec",
    "load_specs",
    "dump_spec",
    "spec_to_dict",
    "spec_from_dict",
]
