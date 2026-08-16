"""Phase 1 orchestration: create -> expand -> review -> enrich -> refs -> conflicts."""

import json

import pytest

from toolguard.buildtime.gen_spec_v2.data_types import load_spec
from toolguard.buildtime.gen_spec_v2.spec_generator import (
    PHASE_ONE_STEPS,
    REJECTED_FILENAME,
    SpecV2Options,
    SpecV2Step,
    ToolGuardSpecGeneratorV2,
)

from .conftest import FakeLLM

OWN_DATA_RULE = (
    "An employee may view and edit only their **own data** — home address, "
    "passport, and bank account."
)
HR_RULE = "**HR** may view and edit all employees' data."

ONE_VOTE = SpecV2Options(
    review_votes=1, feasibility_votes=1, add_iterations=1, steps=PHASE_ONE_STEPS
)


def create_response(items):
    return {
        "tool_info": {"is_read_only": True, "user_enrichment": "sensitive PII"},
        "policy_items": items,
    }


def item(
    item_id, references, name="Read limited to self", description="Own data only."
):
    return {
        "id": item_id,
        "name": name,
        "description": description,
        "references": references,
    }


KEEP = {"is_relevant": True, "can_be_validated": True, "reason": "governs this tool"}
DROP = {"is_relevant": False, "can_be_validated": True, "reason": "orchestration rule"}
ENRICH_SELF = {
    "trigger": "pre_tool",
    "requires": {
        "system_vars": ["user_id"],
        "tool_history": [],
        "message_history": False,
    },
    "references": [OWN_DATA_RULE],
    "pending_for_user": [],
}
EXAMPLES = {
    "compliance_examples": ["Bob reads his own bank account."],
    "violation_examples": ["Bob reads a colleague's bank account."],
}


def generator(llm, tmp_path, mini_policy, mini_tools, mini_sys_var, options=ONE_VOTE):
    return ToolGuardSpecGeneratorV2(
        llm=llm,
        policy_document=mini_policy,
        tools=mini_tools,
        out_dir=tmp_path,
        sys_var=mini_sys_var,
        options=options,
        source_doc="inputs/policy_doc.md",
    )


@pytest.fixture
def one_item_llm():
    return FakeLLM(
        {
            "create": create_response(
                [item("get_bank_account.read_own", [OWN_DATA_RULE])]
            ),
            "expand": {"policy_items": []},
            "review": KEEP,
            "enrich": ENRICH_SELF,
            "examples": EXAMPLES,
        }
    )


async def test_stages_run_in_order(
    one_item_llm, tmp_path, mini_policy, mini_tools, mini_sys_var
):
    gen = generator(one_item_llm, tmp_path, mini_policy, mini_tools, mini_sys_var)
    await gen.generate_all(tools2guard=["get_bank_account"])
    assert one_item_llm.stages == ["create", "expand", "review", "enrich"]


async def test_a_spec_file_is_written_per_tool_with_items(
    one_item_llm, tmp_path, mini_policy, mini_tools, mini_sys_var
):
    gen = generator(one_item_llm, tmp_path, mini_policy, mini_tools, mini_sys_var)
    result = await gen.generate_all(tools2guard=["get_bank_account"])

    written = tmp_path / "get_bank_account.json"
    assert written.exists()
    assert result.written == [written]
    spec = load_spec(written)
    assert spec.tool_name == "get_bank_account"
    assert spec.source_doc == "inputs/policy_doc.md"
    assert [i.id for i in spec.policy_items] == ["get_bank_account.read_own"]


async def test_enrich_results_land_on_the_item(
    one_item_llm, tmp_path, mini_policy, mini_tools, mini_sys_var
):
    gen = generator(one_item_llm, tmp_path, mini_policy, mini_tools, mini_sys_var)
    await gen.generate_all(tools2guard=["get_bank_account"])
    written = load_spec(tmp_path / "get_bank_account.json").policy_items[0]
    assert written.trigger == "pre_tool"
    assert written.requires.system_vars == ["user_id"]
    assert written.requires.tool_history == []
    assert written.requires.message_history is False


async def test_phase_one_leaves_examples_empty(
    one_item_llm, tmp_path, mini_policy, mini_tools, mini_sys_var
):
    """Examples are phase 2; phase-1 output is knowingly not schema-valid yet."""
    gen = generator(one_item_llm, tmp_path, mini_policy, mini_tools, mini_sys_var)
    await gen.generate_all(tools2guard=["get_bank_account"])
    written = load_spec(tmp_path / "get_bank_account.json").policy_items[0]
    assert written.compliance_examples == []
    assert written.violation_examples == []
    assert "examples" not in one_item_llm.stages


async def test_examples_run_inline_when_the_step_is_enabled(
    one_item_llm, tmp_path, mini_policy, mini_tools, mini_sys_var
):
    options = SpecV2Options(
        review_votes=1,
        feasibility_votes=1,
        add_iterations=1,
        steps=set(SpecV2Step),
    )
    gen = generator(
        one_item_llm, tmp_path, mini_policy, mini_tools, mini_sys_var, options
    )
    await gen.generate_all(tools2guard=["get_bank_account"])
    written = load_spec(tmp_path / "get_bank_account.json").policy_items[0]
    assert written.compliance_examples == ["Bob reads his own bank account."]
    assert written.violation_examples == ["Bob reads a colleague's bank account."]


async def test_a_tool_whose_items_are_all_rejected_gets_no_file(
    tmp_path, mini_policy, mini_tools, mini_sys_var
):
    llm = FakeLLM(
        {
            "create": create_response(
                [item("get_bank_account.orchestration", [OWN_DATA_RULE])]
            ),
            "expand": {"policy_items": []},
            "review": DROP,
            "enrich": ENRICH_SELF,
        }
    )
    gen = generator(llm, tmp_path, mini_policy, mini_tools, mini_sys_var)
    result = await gen.generate_all(tools2guard=["get_bank_account"])

    assert not (tmp_path / "get_bank_account.json").exists()
    assert result.written == []
    assert result.specs == {}


async def test_rejected_items_are_reported_and_written_under_process(
    tmp_path, mini_policy, mini_tools, mini_sys_var
):
    llm = FakeLLM(
        {
            "create": create_response(
                [item("get_bank_account.orchestration", [OWN_DATA_RULE])]
            ),
            "expand": {"policy_items": []},
            "review": DROP,
            "enrich": ENRICH_SELF,
        }
    )
    gen = generator(llm, tmp_path, mini_policy, mini_tools, mini_sys_var)
    result = await gen.generate_all(tools2guard=["get_bank_account"])

    rejected = result.rejected["get_bank_account"]
    assert [r.stage for r in rejected] == ["review"]
    assert rejected[0].reason == "orchestration rule"
    assert rejected[0].item.id == "get_bank_account.orchestration"

    report = json.loads((tmp_path / "process" / REJECTED_FILENAME).read_text())
    assert (
        report["get_bank_account"][0]["item"]["id"] == "get_bank_account.orchestration"
    )
    assert report["get_bank_account"][0]["stage"] == "review"


async def test_the_report_stays_out_of_the_spec_directory(
    one_item_llm, tmp_path, mini_policy, mini_tools, mini_sys_var
):
    """The eval globs work_dir/*.json for specs; a stray file there is a fake tool."""
    gen = generator(one_item_llm, tmp_path, mini_policy, mini_tools, mini_sys_var)
    await gen.generate_all(tools2guard=["get_bank_account"])
    assert sorted(p.name for p in tmp_path.glob("*.json")) == ["get_bank_account.json"]


async def test_an_item_with_no_references_is_never_created(
    tmp_path, mini_policy, mini_tools, mini_sys_var
):
    llm = FakeLLM(
        {
            "create": create_response(
                [
                    item("get_bank_account.grounded", [OWN_DATA_RULE]),
                    item("get_bank_account.invented", []),
                ]
            ),
            "expand": {"policy_items": []},
            "review": KEEP,
            "enrich": ENRICH_SELF,
        }
    )
    gen = generator(llm, tmp_path, mini_policy, mini_tools, mini_sys_var)
    await gen.generate_all(tools2guard=["get_bank_account"])
    spec = load_spec(tmp_path / "get_bank_account.json")
    assert [i.id for i in spec.policy_items] == ["get_bank_account.grounded"]


async def test_a_paraphrased_reference_is_repaired_to_the_verbatim_rule(
    tmp_path, mini_policy, mini_tools, mini_sys_var
):
    llm = FakeLLM(
        {
            "create": create_response(
                [
                    item(
                        "get_bank_account.hr_all",
                        ["HR may view and edit the data of all employees"],
                    )
                ]
            ),
            "expand": {"policy_items": []},
            "review": KEEP,
            "enrich": {**ENRICH_SELF, "references": []},
        }
    )
    gen = generator(llm, tmp_path, mini_policy, mini_tools, mini_sys_var)
    await gen.generate_all(tools2guard=["get_bank_account"])
    spec = load_spec(tmp_path / "get_bank_account.json")
    assert spec.policy_items[0].references == [HR_RULE]
    assert spec.policy_items[0].references[0] in mini_policy


async def test_enrich_cannot_add_a_reference_the_item_did_not_have(
    tmp_path, mini_policy, mini_tools, mini_sys_var
):
    llm = FakeLLM(
        {
            "create": create_response(
                [item("get_bank_account.read_own", [OWN_DATA_RULE])]
            ),
            "expand": {"policy_items": []},
            "review": KEEP,
            "enrich": {**ENRICH_SELF, "references": [OWN_DATA_RULE, HR_RULE]},
        }
    )
    gen = generator(llm, tmp_path, mini_policy, mini_tools, mini_sys_var)
    await gen.generate_all(tools2guard=["get_bank_account"])
    spec = load_spec(tmp_path / "get_bank_account.json")
    assert spec.policy_items[0].references == [OWN_DATA_RULE]


async def test_pending_entries_are_normalized_before_writing(
    tmp_path, mini_policy, mini_tools, mini_sys_var
):
    llm = FakeLLM(
        {
            "create": create_response(
                [item("update_passport.blacklist", [OWN_DATA_RULE])]
            ),
            "expand": {"policy_items": []},
            "review": KEEP,
            "enrich": {
                **ENRICH_SELF,
                "pending_for_user": [
                    {
                        "type": "missing_tool",
                        "detail": "no blacklist tool",
                        "question": "How do we learn blacklist status?",
                    }
                ],
            },
        }
    )
    gen = generator(llm, tmp_path, mini_policy, mini_tools, mini_sys_var)
    await gen.generate_all(tools2guard=["update_passport"])
    pending = (
        load_spec(tmp_path / "update_passport.json").policy_items[0].pending_for_user
    )
    assert [p.type for p in pending] == ["clarification"]
    assert pending[0].suggested_tool is None


async def test_conflicts_are_found_and_attached_when_a_tool_has_two_items(
    tmp_path, mini_policy, mini_tools, mini_sys_var
):
    llm = FakeLLM(
        {
            "create": create_response(
                [
                    item("update_employee.edit_own_or_hr", [OWN_DATA_RULE]),
                    item("update_employee.salary_hr_only", [HR_RULE]),
                ]
            ),
            "expand": {"policy_items": []},
            "review": KEEP,
            "enrich": {**ENRICH_SELF, "references": []},
            "conflicts": {
                "conflicts": [
                    {
                        "id": "conflict.update_employee.salary_scope",
                        "name": "May an employee set their own salary?",
                        "kind": "scope",
                        "conflicting_policies": [
                            "update_employee.edit_own_or_hr",
                            "update_employee.salary_hr_only",
                        ],
                        "description": "Own-data edit permits it; the salary rule denies it.",
                        "question": "Does the salary restriction override own-data edit?",
                    }
                ]
            },
        }
    )
    gen = generator(llm, tmp_path, mini_policy, mini_tools, mini_sys_var)
    await gen.generate_all(tools2guard=["update_employee"])

    spec = load_spec(tmp_path / "update_employee.json")
    assert [c.id for c in spec.conflicts] == ["conflict.update_employee.salary_scope"]
    assert spec.conflicts[0].resolution is None


async def test_one_tools_failure_does_not_cost_the_others(
    tmp_path, mini_policy, mini_tools, mini_sys_var
):
    def create_by_tool(prompt: str):
        if "Tool name: update_passport" in prompt:
            return RuntimeError("gateway returned garbage")
        return create_response([item("t.read_own", [OWN_DATA_RULE])])

    llm = FakeLLM(
        {
            "create": create_by_tool,
            "expand": {"policy_items": []},
            "review": KEEP,
            "enrich": ENRICH_SELF,
        }
    )
    gen = generator(llm, tmp_path, mini_policy, mini_tools, mini_sys_var)
    result = await gen.generate_all(tools2guard=["get_bank_account", "update_passport"])

    assert list(result.failed) == ["update_passport"]
    assert "garbage" in result.failed["update_passport"]
    assert (tmp_path / "get_bank_account.json").exists()
    assert not (tmp_path / "update_passport.json").exists()


async def test_item_ids_are_rewritten_to_the_tool_and_kept_unique(
    tmp_path, mini_policy, mini_tools, mini_sys_var
):
    llm = FakeLLM(
        {
            "create": create_response(
                [
                    item("wrong_tool.Read Own!", [OWN_DATA_RULE]),
                    item("wrong_tool.Read-Own", [OWN_DATA_RULE]),
                ]
            ),
            "expand": {"policy_items": []},
            "review": KEEP,
            "enrich": ENRICH_SELF,
            "conflicts": {"conflicts": []},
        }
    )
    gen = generator(llm, tmp_path, mini_policy, mini_tools, mini_sys_var)
    await gen.generate_all(tools2guard=["get_bank_account"])
    ids = [i.id for i in load_spec(tmp_path / "get_bank_account.json").policy_items]
    assert ids == ["get_bank_account.read_own", "get_bank_account.read_own_2"]


async def test_expand_adds_items_the_create_pass_missed(
    tmp_path, mini_policy, mini_tools, mini_sys_var
):
    llm = FakeLLM(
        {
            "create": create_response(
                [item("get_bank_account.read_own", [OWN_DATA_RULE])]
            ),
            "expand": {"policy_items": [item("get_bank_account.hr_all", [HR_RULE])]},
            "review": KEEP,
            "enrich": {**ENRICH_SELF, "references": []},
            "conflicts": {"conflicts": []},
        }
    )
    gen = generator(llm, tmp_path, mini_policy, mini_tools, mini_sys_var)
    await gen.generate_all(tools2guard=["get_bank_account"])
    ids = [i.id for i in load_spec(tmp_path / "get_bank_account.json").policy_items]
    assert ids == ["get_bank_account.read_own", "get_bank_account.hr_all"]


async def test_skipping_steps_skips_their_calls(
    one_item_llm, tmp_path, mini_policy, mini_tools, mini_sys_var
):
    options = SpecV2Options(steps={SpecV2Step.ENRICH}, feasibility_votes=1)
    gen = generator(
        one_item_llm, tmp_path, mini_policy, mini_tools, mini_sys_var, options
    )
    await gen.generate_all(tools2guard=["get_bank_account"])
    assert one_item_llm.stages == ["create", "enrich"]


async def test_every_tool_is_processed_when_no_subset_is_given(
    one_item_llm, tmp_path, mini_policy, mini_tools, mini_sys_var
):
    gen = generator(one_item_llm, tmp_path, mini_policy, mini_tools, mini_sys_var)
    result = await gen.generate_all()
    assert len(one_item_llm.calls_for("create")) == len(mini_tools)
    assert len(result.specs) == len(mini_tools)


async def test_an_undeclared_system_variable_is_dropped(
    tmp_path, mini_policy, mini_tools, mini_sys_var
):
    """The validator rejects a spec naming a variable system_vars.json lacks."""
    llm = FakeLLM(
        {
            "create": create_response(
                [item("update_passport.blacklist", [OWN_DATA_RULE])]
            ),
            "expand": {"policy_items": []},
            "review": KEEP,
            "enrich": {
                **ENRICH_SELF,
                "requires": {
                    "system_vars": ["user_id", "blacklist"],
                    "tool_history": [],
                    "message_history": False,
                },
            },
        }
    )
    gen = generator(llm, tmp_path, mini_policy, mini_tools, mini_sys_var)
    await gen.generate_all(tools2guard=["update_passport"])
    written = load_spec(tmp_path / "update_passport.json").policy_items[0]
    assert written.requires.system_vars == ["user_id"]


async def test_a_tool_history_entry_naming_an_unknown_tool_is_dropped(
    tmp_path, mini_policy, mini_tools, mini_sys_var
):
    """The validator rejects a tool_history dependency that is not a real tool."""
    llm = FakeLLM(
        {
            "create": create_response(
                [item("get_bank_account.read_own", [OWN_DATA_RULE])]
            ),
            "expand": {"policy_items": []},
            "review": KEEP,
            "enrich": {
                **ENRICH_SELF,
                "requires": {
                    "system_vars": ["user_id"],
                    "tool_history": [
                        {
                            "tool": "get_blacklist_status",
                            "params": {"user_id": "input.arguments.user_id"},
                        },
                        {
                            "tool": "get_direct_reports",
                            "params": {"user_id": "input.extensions.subject.user_id"},
                        },
                    ],
                    "message_history": False,
                },
            },
        }
    )
    gen = generator(llm, tmp_path, mini_policy, mini_tools, mini_sys_var)
    await gen.generate_all(tools2guard=["get_bank_account"])
    written = load_spec(tmp_path / "get_bank_account.json").policy_items[0]
    assert [entry.tool for entry in written.requires.tool_history] == [
        "get_direct_reports"
    ]
