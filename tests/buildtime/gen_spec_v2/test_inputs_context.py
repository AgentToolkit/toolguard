"""Rule extraction from the policy document, system-variable handling, renderers.

The fixture is `tests/examples/employee_mini` -- in-repo, so these tests never
read the benchmark repo.
"""

from pathlib import Path

import pytest

from toolguard.buildtime.gen_spec.data_types import ToolInfo, ToolInfoParam
from toolguard.buildtime.gen_spec_v2.context import (
    GenContext,
    render_policy_rules,
    render_system_vars,
    render_tool_detail,
    render_tools_overview,
)
from toolguard.buildtime.gen_spec_v2.inputs import (
    extract_policy_rules,
    load_system_vars,
    looks_like_html,
)

MINI = Path(__file__).parents[2] / "examples" / "employee_mini" / "inputs"


@pytest.fixture(scope="module")
def policy_text() -> str:
    return (MINI / "policy_doc.md").read_text(encoding="utf-8")


def test_extracts_only_bullets_not_headings_or_prose(policy_text):
    rules = extract_policy_rules(policy_text)
    texts = [rule.text for rule in rules]
    assert (
        "An employee may view and edit only their **own data** — home address, passport, and bank account."
        in texts
    )
    assert not any(t.startswith("#") for t in texts)
    assert not any("performs no authorization of its own" in t for t in texts)


def test_bullet_markers_are_stripped_but_inline_markup_is_kept(policy_text):
    rules = extract_policy_rules(policy_text)
    hr_rule = next(r for r in rules if r.text.startswith("**HR** may view"))
    assert hr_rule.text == "**HR** may view and edit all employees' data."


def test_every_extracted_rule_is_an_exact_substring_of_the_document(policy_text):
    """The schema's reference contract: quotes must appear verbatim in source_doc."""
    for rule in extract_policy_rules(policy_text):
        assert rule.text in policy_text


def test_star_bullets_are_extracted_too():
    rules = extract_policy_rules("* A star bullet rule.\n- A dash bullet rule.\n")
    assert [r.text for r in rules] == ["A star bullet rule.", "A dash bullet rule."]


def test_indented_continuation_lines_join_their_bullet():
    doc = (
        "- A user may be deleted only after the requester provides confirmation "
        "in exactly this form:\n"
        "  `I request to delete user [USER NAME]`.\n"
        "\n"
        "- Another rule.\n"
    )
    rules = extract_policy_rules(doc)
    assert len(rules) == 2
    assert rules[0].text.endswith("`I request to delete user [USER NAME]`.")
    assert rules[1].text == "Another rule."


def test_a_joined_rule_stays_an_exact_substring_of_the_document():
    """Joining must reproduce the document's own whitespace, not invent it."""
    doc = "- First line of the rule:\n  second line of the rule.\n"
    rule = extract_policy_rules(doc)[0]
    assert rule.text in doc


def test_continuation_joining_stops_at_a_blank_line_bullet_or_heading():
    doc = "- Rule one.\n\n  Orphan prose after a blank line.\n- Rule two.\n"
    rules = extract_policy_rules(doc)
    assert [r.text for r in rules] == ["Rule one.", "Rule two."]


def test_rules_carry_a_slug():
    rules = extract_policy_rules("- **HR** may view and edit all employees' data.\n")
    assert rules[0].slug == "hr_may_view_and_edit_all_employees_data"


def test_rendered_html_is_recognised_as_html():
    html = "<ul>\n<li>An employee may view only their own data.</li>\n</ul>"
    assert looks_like_html(html)


def test_markdown_input_is_not_mistaken_for_html(policy_text):
    assert not looks_like_html(policy_text)


def test_load_system_vars_drops_non_subject_keys():
    sys_var = load_system_vars(MINI / "system_vars.json")
    assert sys_var.names == ["user_name", "user_id", "department", "organization"]
    assert "action_list" not in sys_var.names
    assert "action_description" not in sys_var.names


def test_load_system_vars_accepts_an_already_loaded_dict():
    sys_var = load_system_vars({"user_id": 1, "action_list": ["a"]})
    assert sys_var.names == ["user_id"]
    assert sys_var.raw["user_id"] == 1


def test_render_system_vars_shows_enums_for_lists_and_examples_for_scalars():
    rendered = render_system_vars(
        GenContext(
            policy_rules=[],
            system_vars=load_system_vars(
                {"user_id": 1, "department": ["HR", "Engineering"]}
            ),
            tools=[],
        )
    )
    assert "- user_id (input.extensions.subject.user_id): example value = 1" in rendered
    assert (
        "- department (input.extensions.subject.department): allowed values = "
        '["HR", "Engineering"]' in rendered
    )


def test_render_system_vars_says_so_when_there_are_none():
    ctx = GenContext(policy_rules=[], system_vars=load_system_vars({}), tools=[])
    assert "no system variables" in render_system_vars(ctx)


def test_render_policy_rules_lists_each_rule_verbatim_as_a_bullet():
    ctx = GenContext(
        policy_rules=extract_policy_rules("- Rule one.\n- **Rule** two.\n"),
        system_vars=load_system_vars({}),
        tools=[],
    )
    assert render_policy_rules(ctx) == "- Rule one.\n- **Rule** two."


def tool(name: str) -> ToolInfo:
    return ToolInfo(
        name=name,
        summary=f"{name} summary",
        description=f"{name} does a thing",
        parameters={
            "user_id": ToolInfoParam(type="int", description="the user", required=True)
        },
        signature=f"{name}(user_id: int) -> dict",
    )


def test_render_tools_overview_is_one_name_and_description_per_line():
    ctx = GenContext(
        policy_rules=[],
        system_vars=load_system_vars({}),
        tools=[tool("get_employee"), tool("update_employee")],
    )
    assert render_tools_overview(ctx) == (
        "- get_employee: get_employee does a thing\n"
        "- update_employee: update_employee does a thing"
    )


def test_render_tool_detail_exposes_parameters_and_the_signature():
    """post_tool rules need the return type, which only the signature carries."""
    rendered = render_tool_detail(tool("get_employee"))
    assert "get_employee" in rendered
    assert "user_id" in rendered
    assert "get_employee(user_id: int) -> dict" in rendered


def test_html_policy_input_is_rejected_outright(policy_text):
    """HTML is not a supported input: no rules can be extracted from it, and its
    text could never be quoted verbatim from a markdown source_doc."""
    import markdown  # type: ignore[import-untyped]

    from toolguard.buildtime.gen_spec_v2.inputs import HtmlPolicyDocumentError

    with pytest.raises(HtmlPolicyDocumentError) as exc_info:
        extract_policy_rules(markdown.markdown(policy_text))
    assert "markdown" in str(exc_info.value).lower()


def test_markdown_that_merely_mentions_a_tag_is_not_rejected():
    doc = "- The agent must not emit a literal </li> in its reply.\n"
    rules = extract_policy_rules(doc)
    assert len(rules) == 1
