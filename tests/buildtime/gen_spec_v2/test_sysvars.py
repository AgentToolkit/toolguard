"""System variables: loading from a dict or a file, and prompt rendering.

The rendered block is what stops the LLM inventing subject variables, so it
must name every declared variable, its access path, and its domain.
"""

import json

import pytest

from toolguard.buildtime.gen_spec_v2.sysvars import (
    keep_declared,
    load_system_vars,
    render_system_vars,
)

from .conftest import CORPUS_SYSTEM_VARS

EMPLOYEE_VARS = {
    "user_name": "Bob",
    "user_id": 1,
    "department": ["Corporate Leadership", "Engineering", "Product", "HR", "Finance"],
    "organization": ["IBM Corporation", "Red Hat", "Kyndryl"],
}


def test_dict_input_keeps_every_key_in_order():
    sv = load_system_vars(EMPLOYEE_VARS)
    assert sv.names == ["user_name", "user_id", "department", "organization"]


def test_none_input_yields_no_variables():
    assert load_system_vars(None).names == []


def test_path_input_reads_the_file(tmp_path):
    path = tmp_path / "sys_var.json"
    path.write_text(json.dumps(EMPLOYEE_VARS), encoding="utf-8")

    assert load_system_vars(path).names == list(EMPLOYEE_VARS)
    assert load_system_vars(str(path)).raw["user_name"] == "Bob"


def test_non_object_json_is_rejected(tmp_path):
    path = tmp_path / "sys_var.json"
    path.write_text("[1, 2]", encoding="utf-8")

    with pytest.raises(ValueError):
        load_system_vars(path)


def test_list_value_renders_as_allowed_values():
    rendered = render_system_vars(load_system_vars(EMPLOYEE_VARS))

    assert (
        "- organization (input.extensions.subject.organization): allowed values = "
        '["IBM Corporation", "Red Hat", "Kyndryl"]' in rendered
    )


def test_scalar_value_renders_as_an_example():
    rendered = render_system_vars(load_system_vars(EMPLOYEE_VARS))

    assert "- user_id (input.extensions.subject.user_id): example value = 1" in rendered


def test_rendering_without_variables_says_so():
    rendered = render_system_vars(load_system_vars(None))

    assert "no system variables" in rendered.lower()


def test_the_agents_own_action_catalog_is_ignored():
    # Real sys_var files carry the agent's action catalog alongside the acting
    # user's attributes. Those two keys describe the tools, not the subject, and
    # `action_description` is a 35-entry mapping that would be pure prompt noise.
    sv = load_system_vars(
        {
            "user_id": 1,
            "action_list": ["add_employee", "get_employee"],
            "action_description": {"add_employee": "Create a record"},
        }
    )

    assert sv.names == ["user_id"]
    assert "action_description" not in render_system_vars(sv)
    assert "action_list" not in render_system_vars(sv)


def test_a_nested_mapping_is_still_a_subject_variable():
    # sys_var.json is not assumed to be flat: a structured attribute of the
    # acting user is kept and rendered.
    sv = load_system_vars({"entitlements": {"payroll": "read", "pii": "none"}})

    assert sv.names == ["entitlements"]
    assert '"payroll": "read"' in render_system_vars(sv)


def test_a_nested_list_is_still_a_subject_variable():
    sv = load_system_vars({"managed_teams": [{"id": 3, "name": "Platform"}]})

    assert sv.names == ["managed_teams"]
    assert "Platform" in render_system_vars(sv)


def test_the_real_employee_sys_var_file_yields_only_subject_variables():
    sv = load_system_vars(CORPUS_SYSTEM_VARS)

    assert sv.names == ["user_name", "user_id", "department", "organization"]


def test_keep_declared_drops_invented_names():
    sv = load_system_vars(EMPLOYEE_VARS)

    assert keep_declared(["department", "is_admin", "user_id"], sv) == [
        "department",
        "user_id",
    ]


def test_keep_declared_dedupes_and_preserves_order():
    sv = load_system_vars(EMPLOYEE_VARS)

    assert keep_declared(["user_id", "department", "user_id"], sv) == [
        "user_id",
        "department",
    ]
