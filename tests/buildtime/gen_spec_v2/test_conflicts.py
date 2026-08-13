"""Conflict detection within a tool, and routing conflicts onto specs.

Routing is the part that differs from smith: with no `global.json`, a conflict
spanning several tools attaches to each involved tool's spec so every spec
stays self-contained.
"""

from toolguard.buildtime.gen_spec_v2.conflicts import (
    attach_conflicts,
    find_conflicts,
)
from toolguard.buildtime.gen_spec_v2.models import Conflict, PolicyItemV2, SpecV2

from .conftest import FakeLLM


def _item(id_: str, name="a rule") -> PolicyItemV2:
    return PolicyItemV2(id=id_, name=name, description="d", references=["r"])


def _spec(tool: str, *ids: str) -> SpecV2:
    return SpecV2(tool_name=tool, policy_items=[_item(i) for i in ids])


def _raw_conflict(
    id_="conflict.update_employee.scope", policies=("update_employee.a",)
):
    return {
        "id": id_,
        "name": "a conflict",
        "kind": "scope",
        "conflicting_policies": list(policies),
        "description": "when both apply",
        "question": "which wins?",
    }


# --- find_conflicts --------------------------------------------------------


async def test_a_tool_with_one_item_is_not_examined():
    # There is no pair to compare, so no call should be made.
    llm = FakeLLM({"conflicts": {"conflicts": []}})

    await find_conflicts(llm, [_spec("update_employee", "update_employee.a")])

    assert llm.count("conflicts") == 0


async def test_pairwise_calls_are_upper_triangle_only():
    # 4 items -> compare item i against items i+1.. for i in 0..2 = 3 calls,
    # not 12: each prompt stays bounded by one tool's item count.
    llm = FakeLLM({"conflicts": {"conflicts": []}})
    spec = _spec(
        "update_employee",
        "update_employee.a",
        "update_employee.b",
        "update_employee.c",
        "update_employee.d",
    )

    await find_conflicts(llm, [spec])

    assert llm.count("conflicts") == 3


async def test_found_conflicts_are_returned_with_no_resolution():
    llm = FakeLLM({"conflicts": {"conflicts": [_raw_conflict()]}})
    spec = _spec("update_employee", "update_employee.a", "update_employee.b")

    conflicts = await find_conflicts(llm, [spec])

    assert len(conflicts) == 1
    assert conflicts[0].kind == "scope"
    assert conflicts[0].resolution is None


async def test_duplicate_conflicts_are_deduped_by_id():
    llm = FakeLLM({"conflicts": {"conflicts": [_raw_conflict(), _raw_conflict()]}})
    spec = _spec("update_employee", "update_employee.a", "update_employee.b")

    assert len(await find_conflicts(llm, [spec])) == 1


async def test_a_malformed_conflict_entry_is_skipped():
    llm = FakeLLM({"conflicts": {"conflicts": [{"id": "x"}, _raw_conflict()]}})
    spec = _spec("update_employee", "update_employee.a", "update_employee.b")

    conflicts = await find_conflicts(llm, [spec])

    assert [c.id for c in conflicts] == ["conflict.update_employee.scope"]


async def test_a_response_without_a_conflicts_key_is_tolerated():
    llm = FakeLLM({"conflicts": {"unexpected": True}})
    spec = _spec("update_employee", "update_employee.a", "update_employee.b")

    assert await find_conflicts(llm, [spec]) == []


async def test_conflicts_referencing_unknown_items_are_dropped():
    # A conflict must point at real policy items to be actionable.
    llm = FakeLLM({"conflicts": {"conflicts": [_raw_conflict(policies=("made.up",))]}})
    spec = _spec("update_employee", "update_employee.a", "update_employee.b")

    assert await find_conflicts(llm, [spec]) == []


# --- attach_conflicts ------------------------------------------------------


def _conflict(id_, policies) -> Conflict:
    return Conflict(
        id=id_,
        name="c",
        kind="scope",
        conflicting_policies=list(policies),
        description="d",
        question="q",
    )


def test_a_single_tool_conflict_attaches_to_that_tool():
    specs = [
        _spec("update_employee", "update_employee.a"),
        _spec("set_passport", "set_passport.a"),
    ]
    conflict = _conflict("c1", ["update_employee.a", "update_employee.b"])

    attach_conflicts(specs, [conflict])

    assert [c.id for c in specs[0].conflicts] == ["c1"]
    assert specs[1].conflicts == []


def test_a_cross_tool_conflict_attaches_to_every_involved_tool():
    specs = [
        _spec("update_employee", "update_employee.a"),
        _spec("set_passport", "set_passport.a"),
        _spec("get_visa", "get_visa.a"),
    ]
    conflict = _conflict("c1", ["update_employee.a", "set_passport.a"])

    attach_conflicts(specs, [conflict])

    assert [c.id for c in specs[0].conflicts] == ["c1"]
    assert [c.id for c in specs[1].conflicts] == ["c1"]
    assert specs[2].conflicts == []


def test_attaching_replaces_rather_than_accumulates():
    # Rerunning detection must not double up conflicts already on the spec.
    spec = _spec("update_employee", "update_employee.a")
    conflict = _conflict("c1", ["update_employee.a"])

    attach_conflicts([spec], [conflict])
    attach_conflicts([spec], [conflict])

    assert len(spec.conflicts) == 1


def test_a_conflict_naming_an_absent_tool_is_ignored():
    spec = _spec("update_employee", "update_employee.a")
    conflict = _conflict("c1", ["nonexistent_tool.a"])

    attach_conflicts([spec], [conflict])

    assert spec.conflicts == []


def test_attaching_nothing_clears_previous_conflicts():
    spec = _spec("update_employee", "update_employee.a")
    spec.conflicts = [_conflict("stale", ["update_employee.a"])]

    attach_conflicts([spec], [])

    assert spec.conflicts == []
