"""The public v2 entrypoints, as the eval runner calls them.

`eval_scripts/run_step1_v1_v2.py` in the evaluate-tool-guard repo imports
`SpecV2Options` and `generate_guard_specs_v2_full` from `toolguard.buildtime` and
passes `system_vars` as a PATH. These tests pin that contract.
"""

import json

import pytest

from toolguard.buildtime.gen_spec_v2.data_types import load_spec

from .conftest import MINI_INPUTS, FakeLLM, load_mini_tools_module

OWN_DATA_RULE = (
    "An employee may view and edit only their **own data** — home address, "
    "passport, and bank account."
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


@pytest.fixture
def llm():
    return FakeLLM(
        {
            "create": CREATE,
            "expand": {"policy_items": []},
            "review": {"is_relevant": True, "can_be_validated": True, "reason": "ok"},
            "enrich": ENRICH,
            "examples": EXAMPLES,
        }
    )


@pytest.fixture
def mini_callables():
    """The mini tools as plain callables, the way a benchmark supplies them."""
    module = load_mini_tools_module("employee_mini_tools_entry")
    return [module.get_bank_account, module.update_passport]


def test_the_v2_entrypoints_are_exported_from_toolguard_buildtime():
    import toolguard.buildtime as buildtime

    for name in (
        "generate_guard_specs_v2",
        "generate_guard_specs_v2_full",
        "generate_guard_examples_v2",
        "SpecV2Options",
        "SpecV2Step",
    ):
        assert name in buildtime.__all__, f"{name} missing from __all__"
        assert hasattr(buildtime, name)


def test_everything_a_caller_needs_for_the_v2_to_v1_handover_is_exported():
    """A benchmark repo should not have to import from gen_spec_v2 submodules."""
    import toolguard.buildtime as buildtime

    for name in (
        "to_v1_spec",
        "to_v1_specs",
        "skip_for",
        "skip_reasons",
        "load_spec_v2",
        "dump_spec_v2",
    ):
        assert name in buildtime.__all__, f"{name} missing from __all__"
        assert hasattr(buildtime, name)


async def test_the_documented_end_to_end_flow_runs(llm, tmp_path, mini_callables):
    """Generate v2, hand it to v1, and get specs gen_py would accept."""
    from toolguard.buildtime import (
        SpecV2Options,
        ToolGuardSpec,
        generate_guard_specs_v2_full,
        load_spec_v2,
        to_v1_specs,
    )

    specs_v2 = await generate_guard_specs_v2_full(
        policy_text=(MINI_INPUTS / "policy_doc.md").read_text(encoding="utf-8"),
        tools=mini_callables,
        llm=llm,
        work_dir=tmp_path,
        system_vars=str(MINI_INPUTS / "system_vars.json"),
        source_doc="inputs/policy_doc.md",
        options=SpecV2Options(review_votes=1, feasibility_votes=1),
    )

    specs_v1 = to_v1_specs(specs_v2)
    assert all(isinstance(spec, ToolGuardSpec) for spec in specs_v1)

    reloaded = load_spec_v2(tmp_path / "get_bank_account.json")
    assert reloaded.tool_name == "get_bank_account"
    assert to_v1_specs([reloaded])[0].tool_name == "get_bank_account"


async def test_full_run_accepts_callables_and_a_system_vars_path(
    llm, tmp_path, mini_callables, schema_validator
):
    from toolguard.buildtime import SpecV2Options, generate_guard_specs_v2_full

    specs = await generate_guard_specs_v2_full(
        policy_text=(MINI_INPUTS / "policy_doc.md").read_text(encoding="utf-8"),
        tools=mini_callables,
        llm=llm,
        work_dir=tmp_path,
        system_vars=str(MINI_INPUTS / "system_vars.json"),
        source_doc="inputs/policy_doc.md",
        options=SpecV2Options(max_concurrency=2, review_votes=1, feasibility_votes=1),
    )

    assert {spec.tool_name for spec in specs} == {"get_bank_account", "update_passport"}
    written = load_spec(tmp_path / "get_bank_account.json")
    assert written.source_doc == "inputs/policy_doc.md"
    assert not list(schema_validator.iter_errors(written.to_dict()))


async def test_policies_only_run_skips_examples(llm, tmp_path, mini_callables):
    from toolguard.buildtime import SpecV2Options, generate_guard_specs_v2

    await generate_guard_specs_v2(
        policy_text=(MINI_INPUTS / "policy_doc.md").read_text(encoding="utf-8"),
        tools=mini_callables,
        llm=llm,
        work_dir=tmp_path,
        system_vars=str(MINI_INPUTS / "system_vars.json"),
        options=SpecV2Options(review_votes=1, feasibility_votes=1),
    )
    assert "examples" not in llm.stages
    assert (
        load_spec(tmp_path / "get_bank_account.json")
        .policy_items[0]
        .compliance_examples
        == []
    )


async def test_examples_entrypoint_completes_a_policies_only_run(
    llm, tmp_path, mini_callables, schema_validator
):
    from toolguard.buildtime import (
        SpecV2Options,
        generate_guard_examples_v2,
        generate_guard_specs_v2,
    )

    options = SpecV2Options(review_votes=1, feasibility_votes=1)
    policy_text = (MINI_INPUTS / "policy_doc.md").read_text(encoding="utf-8")
    await generate_guard_specs_v2(
        policy_text=policy_text,
        tools=mini_callables,
        llm=llm,
        work_dir=tmp_path,
        system_vars=str(MINI_INPUTS / "system_vars.json"),
        options=options,
    )

    specs = await generate_guard_examples_v2(
        tools=mini_callables,
        specs=tmp_path,
        llm=llm,
        work_dir=tmp_path,
        system_vars=str(MINI_INPUTS / "system_vars.json"),
        options=options,
    )

    assert {spec.tool_name for spec in specs} == {"get_bank_account", "update_passport"}
    for spec in specs:
        assert not list(schema_validator.iter_errors(spec.to_dict()))


async def test_tools2guard_limits_the_run(llm, tmp_path, mini_callables):
    from toolguard.buildtime import SpecV2Options, generate_guard_specs_v2_full

    await generate_guard_specs_v2_full(
        policy_text=(MINI_INPUTS / "policy_doc.md").read_text(encoding="utf-8"),
        tools=mini_callables,
        llm=llm,
        work_dir=tmp_path,
        system_vars=str(MINI_INPUTS / "system_vars.json"),
        tools2guard=["update_passport"],
        options=SpecV2Options(review_votes=1, feasibility_votes=1),
    )
    assert sorted(p.name for p in tmp_path.glob("*.json")) == ["update_passport.json"]


async def test_html_policy_text_is_rejected_before_any_model_call(
    llm, tmp_path, mini_callables
):
    """A caller that renders the document to HTML gets a hard error, not an empty run."""
    import markdown  # type: ignore[import-untyped]

    from toolguard.buildtime import SpecV2Options, generate_guard_specs_v2
    from toolguard.buildtime.gen_spec_v2.inputs import HtmlPolicyDocumentError

    html = markdown.markdown(
        (MINI_INPUTS / "policy_doc.md").read_text(encoding="utf-8")
    )

    with pytest.raises(HtmlPolicyDocumentError):
        await generate_guard_specs_v2(
            policy_text=html,
            tools=mini_callables,
            llm=llm,
            work_dir=tmp_path,
            system_vars=str(MINI_INPUTS / "system_vars.json"),
            options=SpecV2Options(review_votes=1, feasibility_votes=1),
        )

    assert llm.calls == [], "no model call should be made for an unusable document"
    assert list(tmp_path.glob("*.json")) == []


async def test_system_vars_may_also_be_passed_as_a_dict(llm, tmp_path, mini_callables):
    from toolguard.buildtime import SpecV2Options, generate_guard_specs_v2

    sys_var = json.loads((MINI_INPUTS / "system_vars.json").read_text(encoding="utf-8"))
    specs = await generate_guard_specs_v2(
        policy_text=(MINI_INPUTS / "policy_doc.md").read_text(encoding="utf-8"),
        tools=mini_callables,
        llm=llm,
        work_dir=tmp_path,
        system_vars=sys_var,
        options=SpecV2Options(review_votes=1, feasibility_votes=1),
    )
    assert specs[0].policy_items[0].requires.system_vars == ["user_id"]
