"""Prompt assembly: every stage must see the inputs it is judging against.

In v1 the feasibility reviewer was never shown the system variables it was
implicitly judging enforceability against. These tests pin the inputs each
stage receives so that cannot silently regress.
"""

import pytest

from toolguard.buildtime.gen_spec.data_types import ToolInfo, ToolInfoParam
from toolguard.buildtime.gen_spec_v2 import prompts
from toolguard.buildtime.gen_spec_v2.context import GenContext

POLICY = "- **HR** may view and edit all employees' data.\n"

TOOL = ToolInfo(
    name="update_employee",
    summary="",
    description="Update an employee",
    parameters={"user_id": ToolInfoParam(type="int", description="who", required=True)},
    signature="update_employee(user_id: int) -> dict",
)

OTHER = ToolInfo(
    name="get_employee",
    summary="",
    description="Read an employee",
    parameters={},
    signature="get_employee(user_id: int) -> dict",
)

ITEM = {
    "id": "update_employee.hr_only",
    "name": "HR only",
    "description": "Only HR may edit",
    "references": ["**HR** may view and edit all employees' data."],
}


def _ctx() -> GenContext:
    return GenContext.build(POLICY, [TOOL, OTHER], {"department": ["HR", "Finance"]})


@pytest.mark.parametrize(
    "name",
    ["create", "expand", "review", "enrich", "examples", "conflicts"],
)
def test_every_system_prompt_loads_and_demands_json(name):
    system = prompts.system(name)

    assert system.strip()
    assert "JSON" in system


def test_json_only_suffix_is_appended():
    assert "first character" in prompts.system("create").lower()


def test_create_user_content_carries_policy_tool_and_system_vars():
    content = prompts.create_user(_ctx(), TOOL)

    assert POLICY.strip() in content
    assert "update_employee(user_id: int)" in content
    assert "input.extensions.subject.department" in content
    assert "- get_employee: Read an employee" in content


def test_expand_user_content_lists_existing_items():
    content = prompts.expand_user(_ctx(), TOOL, [ITEM])

    assert "update_employee.hr_only" in content
    assert POLICY.strip() in content


def test_review_user_content_shows_system_vars_and_other_tools():
    content = prompts.review_user(_ctx(), TOOL, ITEM)

    # v1's reviewer judged "can this be validated" without ever seeing these.
    assert "input.extensions.subject.department" in content
    assert "get_employee" in content


def test_enrich_user_content_carries_the_policy_for_reference_validation():
    content = prompts.enrich_user(_ctx(), TOOL, ITEM)

    assert POLICY.strip() in content
    assert "input.extensions.subject.department" in content
    assert "get_employee" in content


def test_enrich_user_content_excludes_the_tool_being_enriched_from_other_tools():
    content = prompts.enrich_user(_ctx(), TOOL, ITEM)
    others_block = content.split("Other tools")[1]

    assert "get_employee" in others_block
    assert "- update_employee:" not in others_block


def test_examples_user_content_carries_system_var_values():
    content = prompts.examples_user(_ctx(), TOOL, ITEM)

    assert "Finance" in content
    assert "Only HR may edit" in content


def test_conflicts_user_content_names_the_tool_and_both_sides():
    other_item = {**ITEM, "id": "update_employee.self_service"}
    content = prompts.conflicts_user("update_employee", ITEM, [other_item])

    assert "update_employee" in content
    assert "update_employee.hr_only" in content
    assert "update_employee.self_service" in content
