"""The per-tool pipeline and the three public entry points."""

import json

import pytest

from toolguard.buildtime.gen_spec_v2.models import PendingType, Trigger
from toolguard.buildtime.gen_spec_v2.pipeline import (
    SpecV2Options,
    generate_guard_specs_v2,
    generate_guard_specs_v2_full,
    generate_spec_conflicts_v2,
)
from toolguard.buildtime.gen_spec_v2.serialize import load_spec

from .conftest import POLICY, SYSTEM_VARS, FakeLLM, make_tool

HR_RULE = "**HR** may view and edit all employees' data."
SALARY_RULE = "When an employee's **salary** is set or updated, it must be a positive amount (greater than zero)."

TOOLS = [
    make_tool("update_employee", "Update an employee"),
    make_tool("get_employee", "Read"),
]


def _responses(**overrides):
    base = {
        "create": {
            "tool_info": {"is_read_only": False, "user_enrichment": "writes"},
            "policy_items": [
                {
                    "slug": "hr_only",
                    "name": "HR only may edit",
                    "description": "only HR",
                    "references": [HR_RULE],
                },
                {
                    "slug": "salary_positive",
                    "name": "Salary must be positive",
                    "description": "salary > 0",
                    "references": [SALARY_RULE],
                },
            ],
        },
        "expand": {"policy_items": []},
        "review": {"is_relevant": True, "can_be_validated": True, "reason": "yes"},
        "enrich": lambda content: (
            {
                "trigger": "pre_tool",
                "requires": {
                    "system_vars": ["department"] if "only HR" in content else [],
                    "tool_history": None,
                    "message_history": None,
                },
                "references": [HR_RULE] if "only HR" in content else [SALARY_RULE],
                "pending_for_user": [],
            }
        ),
        "examples": {
            "compliance_examples": ["An HR user edits a record."],
            "violation_examples": ["An engineer edits another record."],
        },
        "conflicts": {"conflicts": []},
    }
    base.update(overrides)
    return base


async def test_specs_are_written_one_file_per_tool(tmp_path):
    llm = FakeLLM(_responses())

    specs = await generate_guard_specs_v2(
        POLICY, TOOLS, llm, tmp_path, system_vars=SYSTEM_VARS, source_doc="policy.md"
    )

    assert {s.tool_name for s in specs} == {"update_employee", "get_employee"}
    assert (tmp_path / "update_employee.json").exists()
    assert load_spec(tmp_path / "update_employee.json").source_doc == "policy.md"


async def test_every_stage_contributes_to_the_written_spec(tmp_path):
    llm = FakeLLM(_responses())

    await generate_guard_specs_v2(
        POLICY, TOOLS[:1], llm, tmp_path, system_vars=SYSTEM_VARS
    )
    spec = load_spec(tmp_path / "update_employee.json")

    hr = next(i for i in spec.policy_items if i.id == "update_employee.hr_only")
    assert hr.trigger == Trigger.pre_tool
    assert hr.requires.system_vars == ["department"]
    assert hr.compliance_examples == ["An HR user edits a record."]
    assert hr.references == [HR_RULE]
    assert spec.debug.tool_info.user_enrichment == "writes"


async def test_references_are_grounded_against_the_policy_document(tmp_path):
    # The model quotes the rule without its markdown; the written spec should
    # carry the document's exact text.
    responses = _responses()
    responses["create"] = {
        "policy_items": [
            {
                "slug": "hr_only",
                "name": "HR only",
                "description": "only HR",
                "references": ["HR may view and edit all employees' data."],
            }
        ]
    }
    responses["enrich"] = {
        "trigger": "pre_tool",
        "requires": {"system_vars": [], "tool_history": None, "message_history": None},
        "references": [],
        "pending_for_user": [],
    }
    llm = FakeLLM(responses)

    await generate_guard_specs_v2(POLICY, TOOLS[:1], llm, tmp_path)
    spec = load_spec(tmp_path / "update_employee.json")

    assert spec.policy_items[0].references == [HR_RULE]


async def test_tools2guard_limits_which_specs_are_generated(tmp_path):
    llm = FakeLLM(_responses())

    specs = await generate_guard_specs_v2(
        POLICY, TOOLS, llm, tmp_path, tools2guard=["update_employee"]
    )

    assert [s.tool_name for s in specs] == ["update_employee"]
    assert not (tmp_path / "get_employee.json").exists()


async def test_an_unknown_tool_in_tools2guard_is_rejected(tmp_path):
    llm = FakeLLM(_responses())

    with pytest.raises(ValueError, match="nope"):
        await generate_guard_specs_v2(
            POLICY, TOOLS, llm, tmp_path, tools2guard=["nope"]
        )


async def test_a_tool_with_no_items_still_gets_a_spec_file(tmp_path):
    # An empty spec is a real answer — "no rule governs this tool" — and its
    # absence would otherwise be indistinguishable from a failed run.
    llm = FakeLLM(_responses(create={"policy_items": []}))

    await generate_guard_specs_v2(POLICY, TOOLS[:1], llm, tmp_path)

    assert (tmp_path / "update_employee.json").exists()
    assert load_spec(tmp_path / "update_employee.json").policy_items == []


async def test_pending_gaps_reach_the_written_spec(tmp_path):
    responses = _responses()
    responses["enrich"] = {
        "trigger": "pre_tool",
        "requires": {"system_vars": [], "tool_history": None, "message_history": None},
        "references": [],
        "pending_for_user": [
            {
                "type": "missing_variable",
                "detail": "no blacklist variable exists",
                "question": "where does blacklist status come from?",
                "suggested_source": "system_vars:blacklist",
            }
        ],
    }
    llm = FakeLLM(responses)

    await generate_guard_specs_v2(POLICY, TOOLS[:1], llm, tmp_path)
    spec = load_spec(tmp_path / "update_employee.json")

    pending = spec.policy_items[0].pending_for_user[0]
    assert pending.type == PendingType.missing_var
    assert pending.suggested_source == "system_vars:blacklist"


async def test_a_failing_tool_does_not_abort_the_others(tmp_path):
    class Boom(FakeLLM):
        async def chat_json(self, messages):
            # Key on the tool under generation, not the catalog every prompt
            # carries, so only get_employee's pipeline fails.
            if "Tool name: get_employee" in messages[-1]["content"]:
                raise RuntimeError("model exploded")
            return await super().chat_json(messages)

    llm = Boom(_responses())

    specs = await generate_guard_specs_v2(POLICY, TOOLS, llm, tmp_path)

    assert [s.tool_name for s in specs] == ["update_employee"]


async def test_on_tool_error_raise_propagates(tmp_path):
    class Boom(FakeLLM):
        async def chat_json(self, messages):
            raise RuntimeError("model exploded")

    llm = Boom(_responses())

    with pytest.raises(RuntimeError, match="model exploded"):
        await generate_guard_specs_v2(
            POLICY,
            TOOLS,
            llm,
            tmp_path,
            options=SpecV2Options(on_tool_error="raise"),
        )


async def test_examples_can_be_switched_off(tmp_path):
    llm = FakeLLM(_responses())

    await generate_guard_specs_v2(
        POLICY,
        TOOLS[:1],
        llm,
        tmp_path,
        options=SpecV2Options(include_examples=False),
    )

    assert llm.count("examples") == 0


async def test_system_vars_can_come_from_a_file(tmp_path):
    path = tmp_path / "sys_var.json"
    path.write_text(json.dumps(SYSTEM_VARS), encoding="utf-8")
    llm = FakeLLM(_responses())

    await generate_guard_specs_v2(
        POLICY, TOOLS[:1], llm, tmp_path / "out", system_vars=path
    )
    spec = load_spec(tmp_path / "out" / "update_employee.json")

    hr = next(i for i in spec.policy_items if i.id == "update_employee.hr_only")
    assert hr.requires.system_vars == ["department"]


# --- conflicts entry point -------------------------------------------------


async def test_conflicts_entry_point_loads_specs_from_disk(tmp_path):
    llm = FakeLLM(_responses())
    await generate_guard_specs_v2(POLICY, TOOLS[:1], llm, tmp_path)

    conflict_llm = FakeLLM(
        _responses(
            conflicts={
                "conflicts": [
                    {
                        "id": "conflict.update_employee.scope",
                        "name": "scope clash",
                        "kind": "scope",
                        "conflicting_policies": [
                            "update_employee.hr_only",
                            "update_employee.salary_positive",
                        ],
                        "description": "both apply",
                        "question": "which wins?",
                    }
                ]
            }
        )
    )

    specs = await generate_spec_conflicts_v2(conflict_llm, tmp_path)

    assert [c.id for c in specs[0].conflicts] == ["conflict.update_employee.scope"]
    assert load_spec(tmp_path / "update_employee.json").conflicts


async def test_conflicts_entry_point_leaves_other_specs_untouched(tmp_path):
    llm = FakeLLM(_responses())
    await generate_guard_specs_v2(POLICY, TOOLS, llm, tmp_path)
    before = (tmp_path / "get_employee.json").read_text(encoding="utf-8")

    await generate_spec_conflicts_v2(FakeLLM(_responses()), tmp_path)

    assert (tmp_path / "get_employee.json").read_text(encoding="utf-8") == before


async def test_regenerating_one_tool_leaves_the_other_file_alone(tmp_path):
    llm = FakeLLM(_responses())
    await generate_guard_specs_v2(POLICY, TOOLS, llm, tmp_path)
    before = (tmp_path / "get_employee.json").read_text(encoding="utf-8")

    await generate_guard_specs_v2(
        POLICY, TOOLS, FakeLLM(_responses()), tmp_path, tools2guard=["update_employee"]
    )

    assert (tmp_path / "get_employee.json").read_text(encoding="utf-8") == before


# --- all-in-one ------------------------------------------------------------


async def test_full_run_generates_specs_then_conflicts(tmp_path):
    llm = FakeLLM(_responses())

    specs = await generate_guard_specs_v2_full(
        POLICY, TOOLS, llm, tmp_path, system_vars=SYSTEM_VARS
    )

    assert {s.tool_name for s in specs} == {"update_employee", "get_employee"}
    assert llm.count("create") == 2
    assert llm.count("conflicts") > 0
