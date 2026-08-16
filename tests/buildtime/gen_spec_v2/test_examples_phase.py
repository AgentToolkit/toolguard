"""Phase 2: examples turn phase-1 output into schema-valid specs."""

import pytest

from toolguard.buildtime.gen_spec_v2.data_types import load_spec
from toolguard.buildtime.gen_spec_v2.spec_generator import (
    PHASE_ONE_STEPS,
    SpecV2Options,
    ToolGuardSpecGeneratorV2,
)

from .conftest import FakeLLM

OWN_DATA_RULE = (
    "An employee may view and edit only their **own data** — home address, "
    "passport, and bank account."
)
PHASE_ONE = SpecV2Options(
    review_votes=1, feasibility_votes=1, add_iterations=1, steps=PHASE_ONE_STEPS
)

CREATE = {
    "tool_info": {"is_read_only": True, "user_enrichment": "sensitive PII"},
    "policy_items": [
        {
            "id": "get_bank_account.read_own",
            "name": "Bank-account read limited to self",
            "description": "A user may read only their own bank account.",
            "references": [OWN_DATA_RULE],
        }
    ],
}
ENRICH = {
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


def make_generator(llm, tmp_path, mini_policy, mini_tools, mini_sys_var):
    return ToolGuardSpecGeneratorV2(
        llm=llm,
        policy_document=mini_policy,
        tools=mini_tools,
        out_dir=tmp_path,
        sys_var=mini_sys_var,
        options=PHASE_ONE,
        source_doc="inputs/policy_doc.md",
    )


@pytest.fixture
def phase_one_llm():
    return FakeLLM(
        {
            "create": CREATE,
            "expand": {"policy_items": []},
            "review": {"is_relevant": True, "can_be_validated": True, "reason": "ok"},
            "enrich": ENRICH,
        }
    )


async def test_phase_one_output_is_not_yet_schema_valid(
    phase_one_llm, tmp_path, mini_policy, mini_tools, mini_sys_var, schema_validator
):
    """Examples are minItems 1, so policies alone cannot satisfy the schema."""
    gen = make_generator(phase_one_llm, tmp_path, mini_policy, mini_tools, mini_sys_var)
    await gen.generate_all(tools2guard=["get_bank_account"])

    spec = load_spec(tmp_path / "get_bank_account.json")
    errors = [e.message for e in schema_validator.iter_errors(spec.to_dict())]
    assert errors, "phase-1 output unexpectedly validated"
    assert any("should be non-empty" in e or "[] is too short" in e for e in errors)


async def test_adding_examples_makes_the_spec_schema_valid(
    phase_one_llm, tmp_path, mini_policy, mini_tools, mini_sys_var, schema_validator
):
    gen = make_generator(phase_one_llm, tmp_path, mini_policy, mini_tools, mini_sys_var)
    await gen.generate_all(tools2guard=["get_bank_account"])

    examples_llm = FakeLLM({"examples": EXAMPLES})
    gen2 = ToolGuardSpecGeneratorV2(
        llm=examples_llm,
        policy_document=mini_policy,
        tools=mini_tools,
        out_dir=tmp_path,
        sys_var=mini_sys_var,
        options=PHASE_ONE,
        source_doc="inputs/policy_doc.md",
    )
    result = await gen2.add_examples(gen2.load_specs())

    assert list(result.specs) == ["get_bank_account"]
    spec = load_spec(tmp_path / "get_bank_account.json")
    assert not list(schema_validator.iter_errors(spec.to_dict()))
    assert spec.policy_items[0].compliance_examples == EXAMPLES["compliance_examples"]


async def test_load_specs_ignores_the_process_directory(
    phase_one_llm, tmp_path, mini_policy, mini_tools, mini_sys_var
):
    gen = make_generator(phase_one_llm, tmp_path, mini_policy, mini_tools, mini_sys_var)
    await gen.generate_all(tools2guard=["get_bank_account"])
    assert [spec.tool_name for spec in gen.load_specs()] == ["get_bank_account"]


async def test_an_item_whose_examples_stay_empty_is_rejected_and_retried_once(
    tmp_path, mini_policy, mini_tools, mini_sys_var
):
    empty_llm = FakeLLM(
        {"examples": {"compliance_examples": [], "violation_examples": []}}
    )
    gen = ToolGuardSpecGeneratorV2(
        llm=empty_llm,
        policy_document=mini_policy,
        tools=mini_tools,
        out_dir=tmp_path,
        sys_var=mini_sys_var,
        options=PHASE_ONE,
        source_doc="inputs/policy_doc.md",
    )
    from toolguard.buildtime.gen_spec_v2.data_types import (
        PolicyItemV2,
        ToolGuardSpecV2,
    )

    spec = ToolGuardSpecV2(
        tool_name="get_bank_account",
        source_doc="inputs/policy_doc.md",
        policy_items=[
            PolicyItemV2(
                id="get_bank_account.read_own",
                name="n",
                description="d",
                references=[OWN_DATA_RULE],
            )
        ],
    )
    result = await gen.add_examples([spec])

    assert len(empty_llm.calls_for("examples")) == 2, "should retry once"
    assert [r.stage for r in result.rejected["get_bank_account"]] == ["examples"]
    assert result.specs == {}
    assert not (tmp_path / "get_bank_account.json").exists()


async def test_a_spec_naming_an_unknown_tool_is_reported_not_guessed_at(
    tmp_path, mini_policy, mini_tools, mini_sys_var
):
    from toolguard.buildtime.gen_spec_v2.data_types import (
        PolicyItemV2,
        ToolGuardSpecV2,
    )

    gen = ToolGuardSpecGeneratorV2(
        llm=FakeLLM({"examples": EXAMPLES}),
        policy_document=mini_policy,
        tools=mini_tools,
        out_dir=tmp_path,
        sys_var=mini_sys_var,
        options=PHASE_ONE,
    )
    spec = ToolGuardSpecV2(
        tool_name="delete_everything",
        source_doc="inputs/policy_doc.md",
        policy_items=[
            PolicyItemV2(id="delete_everything.x", name="n", description="d")
        ],
    )
    result = await gen.add_examples([spec])
    assert "delete_everything" in result.failed
    assert result.specs == {}
