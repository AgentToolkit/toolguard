"""The adapter's contract with `gen_py`, checked without calling an LLM.

`generate_guards_code` needs a model to write guard bodies, but everything it
does to a spec *before* that is deterministic: it copies the spec, drops
skipped items, drops specs left empty, and derives python identifiers from
each item's name. Those steps are what an adapter change would break, so they
are exercised here directly against the real `gen_py` helpers.

The full path — v2 -> adapter -> generated guards that compile and pass their
own tests — is `tests/buildtime/e2e/test_gen_spec_v2_codegen.py`, which needs
LLM credentials.
"""

from pathlib import Path

import pytest

from toolguard.buildtime.gen_py.naming_conv import (
    guard_fn_name,
    guard_item_fn_module_name,
    guard_item_fn_name,
)
from toolguard.buildtime.gen_py.naming_conv import (
    # aliased: pytest would collect a module-level name starting with `test_`
    test_fn_module_name as item_test_module_name,
)
from toolguard.buildtime.gen_spec_v2.adapter import spec_v2_to_v1, specs_v2_to_v1
from toolguard.buildtime.gen_spec_v2.models import PolicyItemV2, SpecV2
from toolguard.buildtime.gen_spec_v2.serialize import load_spec
from toolguard.runtime.data_types import ToolGuardSpec

from .conftest import requires_corpus

SPEC_DIR = Path("tests/data/specs_v2")
EMPLOYEE_SPECS = sorted(SPEC_DIR.glob("*.json"))


def _codegen_prepare(specs):
    """Reproduce what `gen_toolguards.generate_*` does before any LLM call."""
    for spec in specs:
        for item in spec.policy_items:
            item.name = item.name.replace(".", "_")

    return [
        spec
        for spec in [
            ToolGuardSpec(
                tool_name=spec.tool_name,
                policy_items=[i for i in spec.policy_items if not i.skip],
            )
            for spec in specs
        ]
        if len(spec.policy_items) > 0
    ]


@requires_corpus
@pytest.mark.parametrize("path", EMPLOYEE_SPECS, ids=lambda p: p.stem)
def test_every_codegen_bound_item_yields_a_usable_python_identifier(path: Path):
    # Only unskipped items are named by codegen. Skipped ones are not, which
    # matters here: `to_snake_case` leaves punctuation alone, so a name
    # containing parentheses would produce an invalid identifier — a
    # pre-existing v1 limitation that the adapter must not walk into.
    v1 = spec_v2_to_v1(load_spec(path))

    assert guard_fn_name(v1).isidentifier()
    for item in v1.policy_items:
        if item.skip:
            continue
        assert guard_item_fn_name(item).isidentifier()
        assert guard_item_fn_module_name(item).isidentifier()


def test_the_disambiguation_suffix_stays_a_valid_identifier():
    # The adapter's own suffix must not introduce punctuation that snake-casing
    # would leave in place.
    spec = SpecV2(
        tool_name="t",
        policy_items=[
            PolicyItemV2(
                id="t.first", name="same rule", description="d", references=["r"]
            ),
            PolicyItemV2(
                id="t.second", name="same rule", description="d", references=["r"]
            ),
        ],
    )

    for item in spec_v2_to_v1(spec).policy_items:
        assert guard_item_fn_name(item).isidentifier()


@requires_corpus
@pytest.mark.parametrize("path", EMPLOYEE_SPECS, ids=lambda p: p.stem)
def test_items_of_one_tool_never_share_a_generated_file(path: Path):
    # Two items mapping to one module name would overwrite each other's guard.
    v1 = spec_v2_to_v1(load_spec(path))
    modules = [guard_item_fn_module_name(i) for i in v1.policy_items]
    tests = [item_test_module_name(i) for i in v1.policy_items]

    assert len(set(modules)) == len(modules)
    assert len(set(tests)) == len(tests)


def test_colliding_names_survive_codegens_dot_replacement():
    # gen_py rewrites '.' to '_' in item names in place, which could re-collide
    # two names the adapter had just disambiguated.
    spec = SpecV2(
        tool_name="t",
        policy_items=[
            PolicyItemV2(id="t.a", name="rule v1.0", description="d", references=["r"]),
            PolicyItemV2(id="t.b", name="rule v1_0", description="d", references=["r"]),
        ],
    )

    prepared = _codegen_prepare([spec_v2_to_v1(spec)])
    modules = [guard_item_fn_module_name(i) for i in prepared[0].policy_items]

    assert len(set(modules)) == 2


@requires_corpus
def test_codegen_receives_only_enforceable_items():
    specs = [spec_v2_to_v1(load_spec(p)) for p in EMPLOYEE_SPECS]

    prepared = _codegen_prepare(specs)

    assert {s.tool_name for s in prepared} == {
        "add_employee",
        "create_time_off_request",
        "set_passport",
        "set_visa",
        "update_employee",
        "update_passport",
        "update_visa",
    }
    assert sum(len(s.policy_items) for s in prepared) == 15


@requires_corpus
def test_a_spec_with_nothing_enforceable_is_dropped_before_codegen():
    specs = [spec_v2_to_v1(load_spec(SPEC_DIR / "get_employee.json"))]

    assert _codegen_prepare(specs) == []


@requires_corpus
def test_the_unattachable_global_spec_never_reaches_codegen():
    # A spec whose tool_name has no tool behind it would make codegen generate
    # a guard for nothing.
    all_specs = [load_spec(p) for p in EMPLOYEE_SPECS]
    tools = [p.stem for p in EMPLOYEE_SPECS if p.stem != "global"]

    converted = specs_v2_to_v1(all_specs, known_tools=tools)

    assert "global" not in {s.tool_name for s in converted}
