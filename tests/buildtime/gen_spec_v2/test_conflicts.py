"""Conflict routing: a conflict must resolve inside the file that carries it.

Detection is within-tool, but a model happily cites a neighbouring tool's items.
The schema requires every id in `conflicting_policies` to exist in the same file
and at least two of them, and says a question spanning several tools is recorded
once per affected tool under a shared id slug. `split_and_attach` is what makes
that true.
"""

from toolguard.buildtime.gen_spec_v2.conflicts import split_and_attach
from toolguard.buildtime.gen_spec_v2.data_types import PolicyItemV2, ToolGuardSpecV2


def spec(tool: str, *slugs: str) -> ToolGuardSpecV2:
    return ToolGuardSpecV2(
        tool_name=tool,
        source_doc="doc.md",
        policy_items=[
            PolicyItemV2(id=f"{tool}.{slug}", name=slug, description="d")
            for slug in slugs
        ],
    )


def raw(conflict_id: str, *policies: str, kind: str = "scope") -> dict:
    return {
        "id": conflict_id,
        "name": "Does the rule bind HR?",
        "kind": kind,
        "conflicting_policies": list(policies),
        "description": "When HR acts on someone else's record.",
        "question": "Does it bind HR?",
    }


def test_a_within_tool_conflict_attaches_to_its_own_spec():
    specs = {"update_employee": spec("update_employee", "edit_own_or_hr", "salary_hr")}
    split_and_attach(
        specs,
        [
            raw(
                "conflict.update_employee.scope",
                "update_employee.edit_own_or_hr",
                "update_employee.salary_hr",
            )
        ],
    )
    conflicts = specs["update_employee"].conflicts
    assert len(conflicts) == 1
    assert conflicts[0].id == "conflict.update_employee.scope"
    assert conflicts[0].resolution is None


def test_a_cross_tool_conflict_is_recorded_once_per_tool_under_a_shared_slug():
    specs = {
        "get_employee": spec("get_employee", "read_own", "outside_ibm"),
        "get_passport": spec("get_passport", "read_own", "outside_ibm"),
    }
    split_and_attach(
        specs,
        [
            raw(
                "conflict.global.ibm_organization_definition",
                "get_employee.read_own",
                "get_employee.outside_ibm",
                "get_passport.read_own",
                "get_passport.outside_ibm",
                kind="definition",
            )
        ],
    )
    employee = specs["get_employee"].conflicts[0]
    passport = specs["get_passport"].conflicts[0]
    assert employee.id == "conflict.get_employee.ibm_organization_definition"
    assert passport.id == "conflict.get_passport.ibm_organization_definition"
    assert employee.conflicting_policies == [
        "get_employee.read_own",
        "get_employee.outside_ibm",
    ]
    assert passport.conflicting_policies == [
        "get_passport.read_own",
        "get_passport.outside_ibm",
    ]


def test_a_tool_contributing_a_single_item_gets_no_copy():
    """minItems is 2: one item cannot conflict with itself."""
    specs = {
        "get_employee": spec("get_employee", "read_own", "outside_ibm"),
        "get_passport": spec("get_passport", "read_own"),
    }
    split_and_attach(
        specs,
        [
            raw(
                "conflict.global.shared",
                "get_employee.read_own",
                "get_employee.outside_ibm",
                "get_passport.read_own",
            )
        ],
    )
    assert len(specs["get_employee"].conflicts) == 1
    assert specs["get_passport"].conflicts == []


def test_a_conflict_no_tool_qualifies_for_is_dropped():
    specs = {"a": spec("a", "one"), "b": spec("b", "one")}
    split_and_attach(specs, [raw("conflict.global.x", "a.one", "b.one")])
    assert specs["a"].conflicts == []
    assert specs["b"].conflicts == []


def test_ids_that_exist_in_no_spec_are_discarded_first():
    specs = {"update_employee": spec("update_employee", "edit_own_or_hr", "salary_hr")}
    split_and_attach(
        specs,
        [
            raw(
                "conflict.update_employee.scope",
                "update_employee.edit_own_or_hr",
                "update_employee.salary_hr",
                "update_employee.hallucinated",
                "no_such_tool.whatever",
            )
        ],
    )
    assert specs["update_employee"].conflicts[0].conflicting_policies == [
        "update_employee.edit_own_or_hr",
        "update_employee.salary_hr",
    ]


def test_duplicate_conflicts_are_deduped_by_id():
    specs = {"update_employee": spec("update_employee", "a", "b")}
    one = raw(
        "conflict.update_employee.scope", "update_employee.a", "update_employee.b"
    )
    split_and_attach(specs, [one, dict(one)])
    assert len(specs["update_employee"].conflicts) == 1


def test_a_malformed_conflict_is_skipped_without_losing_the_others():
    specs = {"update_employee": spec("update_employee", "a", "b")}
    good = raw(
        "conflict.update_employee.scope", "update_employee.a", "update_employee.b"
    )
    split_and_attach(
        specs,
        [
            {"id": "conflict.update_employee.broken"},  # missing everything else
            "not a dict",
            {**good, "kind": "made_up"},  # kind outside the enum
            good,
        ],
    )
    assert [c.id for c in specs["update_employee"].conflicts] == [
        "conflict.update_employee.scope"
    ]


def test_an_undotted_conflict_id_still_yields_a_usable_slug():
    specs = {"update_employee": spec("update_employee", "a", "b")}
    split_and_attach(
        specs, [raw("scope clash!", "update_employee.a", "update_employee.b")]
    )
    assert (
        specs["update_employee"].conflicts[0].id
        == "conflict.update_employee.scope_clash"
    )
