"""The per-run context every stage renders its prompt slice from."""

from toolguard.buildtime.gen_spec.data_types import ToolInfo, ToolInfoParam
from toolguard.buildtime.gen_spec_v2.context import GenContext

POLICY = """# Access Control

## Data Access

- **HR** may view and edit all employees' data.
- Only **HR** may add a new employee.
"""


def _tool(name: str, description: str) -> ToolInfo:
    return ToolInfo(
        name=name,
        summary="",
        description=description,
        parameters={
            "user_id": ToolInfoParam(
                type="int", description="the employee", required=True
            )
        },
        signature=f"{name}(user_id: int) -> dict",
    )


def _ctx() -> GenContext:
    return GenContext.build(
        policy_text=POLICY,
        tools=[
            _tool("get_employee", "Return an employee"),
            _tool("add_employee", "Add"),
        ],
        system_vars={"department": ["HR", "Finance"]},
    )


def test_policy_renders_verbatim_including_headings():
    # v2 does not split the document into bullets, so structure the LLM can
    # use for context (headings, section order) must survive.
    assert _ctx().render_policy() == POLICY


def test_tools_overview_lists_every_tool():
    rendered = _ctx().render_tools_overview()

    assert "- get_employee: Return an employee" in rendered
    assert "- add_employee: Add" in rendered


def test_tool_detail_includes_parameters_and_signature():
    rendered = _ctx().render_tool_detail(_tool("get_employee", "Return an employee"))

    assert "get_employee" in rendered
    assert "user_id" in rendered
    assert "the employee" in rendered


def test_system_vars_render_through_the_context():
    assert "input.extensions.subject.department" in _ctx().render_system_vars()


def test_tool_names_are_exposed_for_validation():
    assert _ctx().tool_names() == ["get_employee", "add_employee"]
