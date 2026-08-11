"""Regenerating examples for specs already on disk.

The counterpart to v1's `generate_guard_examples`: examples are what test
generation works from, and rewording them should not cost a full spec run.
"""

from typing import Any, Dict


from toolguard.buildtime.gen_spec_v2.models import Trigger
from toolguard.buildtime.gen_spec_v2.pipeline import (
    generate_guard_examples_v2,
    generate_guard_specs_v2,
)
from toolguard.buildtime.gen_spec_v2.serialize import load_spec

from .conftest import POLICY, SYSTEM_VARS, FakeLLM, make_tool

HR_RULE = "**HR** may view and edit all employees' data."
TOOLS = [
    make_tool("update_employee", "Update an employee"),
    make_tool("get_employee", "Read"),
]

FIRST_PASS: Dict[str, Any] = {
    "create": {
        "tool_info": {"is_read_only": False, "user_enrichment": "writes"},
        "policy_items": [
            {
                "slug": "hr_only",
                "name": "HR only may edit",
                "description": "only HR",
                "references": [HR_RULE],
            }
        ],
    },
    "expand": {"policy_items": []},
    "review": {"is_relevant": True, "can_be_validated": True, "reason": "yes"},
    "enrich": {
        "trigger": "post_tool",
        "requires": {
            "system_vars": ["department"],
            "tool_history": [{"tool": "get_employee", "params": {}}],
            "message_history": None,
        },
        "references": [HR_RULE],
        "pending_for_user": [],
    },
    "examples": {
        "compliance_examples": ["first compliance"],
        "violation_examples": ["first violation"],
    },
}

SECOND_PASS: Dict[str, Any] = {
    "examples": {
        "compliance_examples": ["An HR user in Finance edits a record."],
        "violation_examples": ["An Engineering user edits another record."],
    }
}


async def _seed(tmp_path) -> None:
    await generate_guard_specs_v2(
        POLICY, TOOLS, FakeLLM(FIRST_PASS), tmp_path, system_vars=SYSTEM_VARS
    )


async def test_examples_are_replaced_on_disk(tmp_path):
    await _seed(tmp_path)
    llm = FakeLLM(SECOND_PASS)

    await generate_guard_examples_v2(
        POLICY, TOOLS, llm, tmp_path, system_vars=SYSTEM_VARS
    )

    spec = load_spec(tmp_path / "update_employee.json")
    assert spec.policy_items[0].compliance_examples == [
        "An HR user in Finance edits a record."
    ]
    assert spec.policy_items[0].violation_examples == [
        "An Engineering user edits another record."
    ]


async def test_only_the_examples_stage_runs(tmp_path):
    await _seed(tmp_path)
    llm = FakeLLM(SECOND_PASS)

    await generate_guard_examples_v2(POLICY, TOOLS, llm, tmp_path)

    assert llm.count("examples") > 0
    assert llm.count("create") == 0
    assert llm.count("expand") == 0
    assert llm.count("review") == 0
    assert llm.count("enrich") == 0


async def test_everything_else_about_the_item_is_preserved(tmp_path):
    await _seed(tmp_path)

    await generate_guard_examples_v2(POLICY, TOOLS, FakeLLM(SECOND_PASS), tmp_path)

    item = load_spec(tmp_path / "update_employee.json").policy_items[0]
    assert item.id == "update_employee.hr_only"
    assert item.trigger == Trigger.post_tool
    assert item.requires.system_vars == ["department"]
    assert item.requires.tool_history is not None
    assert item.references == [HR_RULE]


async def test_a_fixed_example_count_is_requested(tmp_path):
    await _seed(tmp_path)
    llm = FakeLLM(SECOND_PASS)

    await generate_guard_examples_v2(POLICY, TOOLS, llm, tmp_path, example_number=3)

    assert "exactly 3" in llm.calls_for("examples")[0]["content"]


async def test_specs_can_be_passed_instead_of_loaded(tmp_path):
    specs = await generate_guard_specs_v2(
        POLICY, TOOLS, FakeLLM(FIRST_PASS), tmp_path, system_vars=SYSTEM_VARS
    )
    llm = FakeLLM(SECOND_PASS)

    result = await generate_guard_examples_v2(POLICY, TOOLS, llm, tmp_path, specs=specs)

    assert result[0].policy_items[0].compliance_examples == [
        "An HR user in Finance edits a record."
    ]


async def test_a_spec_whose_tool_is_unknown_is_skipped(tmp_path):
    await _seed(tmp_path)
    llm = FakeLLM(SECOND_PASS)

    # Only get_employee is supplied, so update_employee's spec has no tool to
    # render into the prompt and must be left alone rather than guessed at.
    await generate_guard_examples_v2(POLICY, TOOLS[1:], llm, tmp_path)

    spec = load_spec(tmp_path / "update_employee.json")
    assert spec.policy_items[0].compliance_examples == ["first compliance"]


async def test_an_empty_directory_is_not_an_error(tmp_path):
    result = await generate_guard_examples_v2(
        POLICY, TOOLS, FakeLLM(SECOND_PASS), tmp_path
    )

    assert result == []


async def test_rewrite_false_leaves_the_file_untouched(tmp_path):
    await _seed(tmp_path)
    before = (tmp_path / "update_employee.json").read_text(encoding="utf-8")

    result = await generate_guard_examples_v2(
        POLICY, TOOLS, FakeLLM(SECOND_PASS), tmp_path, rewrite=False
    )

    assert (tmp_path / "update_employee.json").read_text(encoding="utf-8") == before
    assert result[0].policy_items[0].compliance_examples == [
        "An HR user in Finance edits a record."
    ]
