"""The v1 spec path, fed by v2-generated specs with `skip` computed in memory.

These mirror what the v1 tests establish -- tool parsing, and the spec shape
`gen_py` consumes -- but with the specs coming out of the v2 generator instead of
v1's. They deliberately assert nothing about generation *quality*; that belongs
in the evaluate-tool-guard benchmark. The question here is only: does the v1
machinery still get what it needs?

No v1 test is touched.
"""

import json
from pathlib import Path

import pytest

from toolguard.buildtime.gen_spec.fn_to_toolinfo import function_to_toolInfo
from toolguard.buildtime.gen_spec.oas_to_toolinfo import openapi_to_toolinfos
from toolguard.buildtime.gen_spec_v2.spec_generator import (
    PHASE_ONE_STEPS,
    SpecV2Options,
    ToolGuardSpecGeneratorV2,
    tools_to_tool_infos,
)
from toolguard.buildtime.gen_spec_v2.v1_compat import to_v1_spec, to_v1_specs
from toolguard.buildtime.utils.open_api import OpenAPI
from toolguard.runtime.data_types import ToolGuardSpec, ToolGuardSpecItem

from ..gen_spec_v2.conftest import MINI_INPUTS, FakeLLM, load_mini_tools_module

OWN_DATA_RULE = (
    "An employee may view and edit only their **own data** — home address, "
    "passport, and bank account."
)
HR_RULE = "**HR** may view and edit all employees' data."

CREATE = {
    "tool_info": {"is_read_only": False, "user_enrichment": "writes employee data"},
    "policy_items": [
        {
            "id": "update_employee.expiry_positive",
            "name": "Salary must be positive",
            "description": "A salary set on the call must be greater than zero.",
            "references": [OWN_DATA_RULE],
        },
        {
            "id": "update_employee.hr_only",
            "name": "Editing others is limited to HR",
            "description": "Only an HR-department user may edit another employee.",
            "references": [HR_RULE],
        },
    ],
}
ARGUMENT_ONLY = {
    "trigger": "pre_tool",
    "requires": {"system_vars": [], "tool_history": [], "message_history": False},
    "references": [OWN_DATA_RULE],
    "pending_for_user": [],
}
NEEDS_SUBJECT = {
    "trigger": "pre_tool",
    "requires": {
        "system_vars": ["department"],
        "tool_history": [],
        "message_history": False,
    },
    "references": [HR_RULE],
    "pending_for_user": [],
}
EXAMPLES = {
    "compliance_examples": ["Bob sets a salary of 100."],
    "violation_examples": ["Bob sets a salary of -1."],
}


def enrich_by_item(prompt: str) -> dict:
    """The second item needs a subject variable; the first is argument-only."""
    return NEEDS_SUBJECT if "hr_only" in prompt else ARGUMENT_ONLY


@pytest.fixture
def v2_llm():
    return FakeLLM(
        {
            "create": CREATE,
            "expand": {"policy_items": []},
            "review": {"is_relevant": True, "can_be_validated": True, "reason": "ok"},
            "enrich": enrich_by_item,
            "examples": EXAMPLES,
            "conflicts": {"conflicts": []},
        }
    )


@pytest.fixture
def mini_callables():
    return [load_mini_tools_module("employee_mini_tools_v2v1").update_employee]


async def generate_v2(llm, tmp_path, callables, steps=None):
    options = SpecV2Options(
        review_votes=1,
        feasibility_votes=1,
        add_iterations=1,
        steps=steps if steps is not None else set(SpecV2Options().steps),
    )
    generator = ToolGuardSpecGeneratorV2(
        llm=llm,
        policy_document=(MINI_INPUTS / "policy_doc.md").read_text(encoding="utf-8"),
        tools=tools_to_tool_infos(callables),
        out_dir=tmp_path,
        sys_var=json.loads((MINI_INPUTS / "system_vars.json").read_text()),
        options=options,
        source_doc="inputs/policy_doc.md",
    )
    result = await generator.generate_all()
    return result


# --- tool parsing is shared, not re-implemented ------------------------------


def test_v2_parses_functions_into_the_same_tool_info_as_v1():
    module = load_mini_tools_module("employee_mini_tools_parity")
    functions = [module.get_bank_account, module.update_employee]

    assert tools_to_tool_infos(functions) == [
        function_to_toolInfo(fn) for fn in functions
    ]


def test_v2_parses_an_openapi_document_into_the_same_tool_info_as_v1():
    oas_path = Path("tests/examples/appointments/appointments_oas.json")
    oas = OpenAPI.load_from(oas_path)
    with open(oas_path, encoding="utf-8") as handle:
        as_dict = json.load(handle)

    assert tools_to_tool_infos(as_dict) == openapi_to_toolinfos(oas)


def test_tool_infos_pass_through_unchanged():
    """A caller that already parsed its tools should not be re-parsed."""
    infos = openapi_to_toolinfos(
        OpenAPI.load_from(Path("tests/examples/appointments/appointments_oas.json"))
    )
    assert tools_to_tool_infos(infos) == infos


# --- v2 specs, seen through v1's eyes ---------------------------------------


async def test_a_v2_generated_spec_becomes_a_valid_v1_spec(
    v2_llm, tmp_path, mini_callables
):
    result = await generate_v2(v2_llm, tmp_path, mini_callables)
    v1_specs = to_v1_specs(list(result.specs.values()))

    assert len(v1_specs) == 1
    spec = v1_specs[0]
    assert isinstance(spec, ToolGuardSpec)
    assert spec.tool_name == "update_employee"
    assert all(isinstance(item, ToolGuardSpecItem) for item in spec.policy_items)


async def test_skip_marks_only_the_item_v1_codegen_cannot_enforce(
    v2_llm, tmp_path, mini_callables
):
    result = await generate_v2(v2_llm, tmp_path, mini_callables)
    spec = to_v1_spec(result.specs["update_employee"])

    by_name = {item.name: item for item in spec.policy_items}
    assert by_name["Salary must be positive"].skip is False
    assert by_name["Editing others is limited to HR"].skip is True


async def test_gen_py_would_receive_only_the_enforceable_items(
    v2_llm, tmp_path, mini_callables
):
    """Reproduces gen_toolguards' own filter over a v2-generated spec."""
    result = await generate_v2(v2_llm, tmp_path, mini_callables)
    spec = to_v1_spec(result.specs["update_employee"])

    enforceable = ToolGuardSpec(
        tool_name=spec.tool_name,
        policy_items=[item for item in spec.policy_items if not item.skip],
    )
    assert [item.name for item in enforceable.policy_items] == [
        "Salary must be positive"
    ]


async def test_the_v1_view_carries_the_content_codegen_reads(
    v2_llm, tmp_path, mini_callables
):
    result = await generate_v2(v2_llm, tmp_path, mini_callables)
    spec = to_v1_spec(result.specs["update_employee"])
    item = next(i for i in spec.policy_items if not i.skip)

    assert item.description
    assert item.references == [OWN_DATA_RULE]
    assert item.compliance_examples == EXAMPLES["compliance_examples"]
    assert item.violation_examples == EXAMPLES["violation_examples"]


async def test_policy_names_survive_v1_code_identifier_conversion(
    v2_llm, tmp_path, mini_callables
):
    """v2 names are sentences; gen_py turns them into module and function names."""
    from toolguard.buildtime.gen_py import naming_conv

    result = await generate_v2(v2_llm, tmp_path, mini_callables)
    spec = to_v1_spec(result.specs["update_employee"])

    for item in spec.policy_items:
        item.name = item.name.replace(".", "_")  # what gen_toolguards does first
        assert naming_conv.guard_item_fn_name(item).isidentifier()
        assert naming_conv.test_fn_module_name(item).isidentifier()


async def test_a_v2_spec_file_on_disk_loads_as_a_v1_spec(
    v2_llm, tmp_path, mini_callables
):
    """The written file needs no conversion: v1 ignores the keys it does not know."""
    await generate_v2(v2_llm, tmp_path, mini_callables)
    loaded = ToolGuardSpec.load(tmp_path / "update_employee.json")

    assert loaded.tool_name == "update_employee"
    assert len(loaded.policy_items) == 2
    assert all(item.skip is False for item in loaded.policy_items), (
        "a file carries no skip; it is computed in memory"
    )


async def test_phase_one_specs_can_also_be_handed_over(
    v2_llm, tmp_path, mini_callables
):
    """Without examples the spec is not schema-valid, but v1 only needs the rules."""
    result = await generate_v2(v2_llm, tmp_path, mini_callables, steps=PHASE_ONE_STEPS)
    spec = to_v1_spec(result.specs["update_employee"])
    item = next(i for i in spec.policy_items if not i.skip)
    assert item.compliance_examples == []
    assert item.description
