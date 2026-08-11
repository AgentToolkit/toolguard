"""Converting a v2 spec into the v1 spec that `gen_py` consumes.

`skip` is the whole point: it marks the items today's codegen and runtime
cannot enforce *correctly*. Generated guards receive `args` + `api` only —
no acting user, no chat history — and there is no post-invocation hook, so a
guard emitted for one of those rules would check the wrong thing rather than
nothing.
"""

from pathlib import Path

import pytest

from toolguard.buildtime.gen_spec_v2.adapter import spec_v2_to_v1, specs_v2_to_v1
from toolguard.buildtime.gen_spec_v2.models import (
    PendingItem,
    PendingType,
    PolicyItemV2,
    Requires,
    SpecToolInfo,
    SpecDebugV2,
    SpecV2,
    ToolHistoryEntry,
    Trigger,
)
from toolguard.buildtime.gen_spec_v2.serialize import load_spec
from toolguard.runtime.data_types import ToolGuardSpec

from .conftest import CORPUS_SPECS_DIR

SPEC_DIR = CORPUS_SPECS_DIR


def _item(name="a rule", **kwargs) -> PolicyItemV2:
    return PolicyItemV2(
        id=kwargs.pop("id", "update_employee.a_rule"),
        name=name,
        description="the rule",
        compliance_examples=["ok"],
        violation_examples=["bad"],
        references=["the source line"],
        **kwargs,
    )


def _spec(*items: PolicyItemV2) -> SpecV2:
    return SpecV2(
        tool_name="update_employee",
        source_doc="policy.md",
        policy_items=list(items),
        debug=SpecDebugV2(tool_info=SpecToolInfo(is_read_only=False)),
    )


# --- skip truth table ------------------------------------------------------


def test_pure_argument_rule_is_not_skipped():
    v1 = spec_v2_to_v1(_spec(_item()))

    assert v1.policy_items[0].skip is False


def test_rule_needing_system_vars_is_skipped():
    item = _item(requires=Requires(system_vars=["department"]))

    assert spec_v2_to_v1(_spec(item)).policy_items[0].skip is True


def test_rule_needing_message_history_is_skipped():
    item = _item(requires=Requires(message_history=True))

    assert spec_v2_to_v1(_spec(item)).policy_items[0].skip is True


def test_post_tool_rule_is_skipped():
    item = _item(trigger=Trigger.post_tool)

    assert spec_v2_to_v1(_spec(item)).policy_items[0].skip is True


def test_rule_with_a_pending_gap_is_skipped():
    item = _item(
        pending_for_user=[
            PendingItem(
                type=PendingType.missing_var, detail="no blacklist", question="where?"
            )
        ]
    )

    assert spec_v2_to_v1(_spec(item)).policy_items[0].skip is True


def test_rule_needing_only_a_prior_tool_call_is_not_skipped():
    # tool_history alone is enforceable today: generated guards get `api`.
    item = _item(
        requires=Requires(tool_history=[ToolHistoryEntry(tool="get_employee")])
    )

    assert spec_v2_to_v1(_spec(item)).policy_items[0].skip is False


# --- fields gen_py depends on ---------------------------------------------


def test_content_fields_survive_the_conversion():
    v1_item = spec_v2_to_v1(_spec(_item())).policy_items[0]

    assert v1_item.name == "a rule"
    assert v1_item.description == "the rule"
    assert v1_item.references == ["the source line"]
    assert v1_item.compliance_examples == ["ok"]
    assert v1_item.violation_examples == ["bad"]


def test_colliding_item_names_are_disambiguated():
    # gen_py derives one module, function, and test file per item.name, so two
    # items sharing a name would overwrite each other's files.
    spec = _spec(
        _item(name="same", id="update_employee.first"),
        _item(name="same", id="update_employee.second"),
    )

    names = [i.name for i in spec_v2_to_v1(spec).policy_items]

    assert len(set(names)) == 2
    assert names[0] == "same"
    assert "second" in names[1]


def test_v2_only_fields_are_preserved_in_debug():
    item = _item(
        trigger=Trigger.post_tool,
        requires=Requires(system_vars=["user_id"]),
    )

    v1_item = spec_v2_to_v1(_spec(item)).policy_items[0]

    assert v1_item.debug["id"] == "update_employee.a_rule"
    assert v1_item.debug["trigger"] == "post_tool"
    assert v1_item.debug["requires"]["system_vars"] == ["user_id"]


def test_spec_level_fields_are_preserved_in_debug():
    v1 = spec_v2_to_v1(_spec(_item()))

    assert v1.tool_name == "update_employee"
    assert v1.debug["source_doc"] == "policy.md"
    assert v1.debug["tool_info"]["is_read_only"] is False


# --- the real corpus -------------------------------------------------------


@pytest.mark.parametrize("path", sorted(SPEC_DIR.glob("*.json")), ids=lambda p: p.stem)
def test_every_ground_truth_spec_converts_and_validates(path: Path):
    v1 = spec_v2_to_v1(load_spec(path))

    # The output must survive v1's own loader, which is what gen_py gets.
    assert ToolGuardSpec.model_validate(v1.model_dump()).tool_name == v1.tool_name


def test_employee_corpus_skips_every_identity_dependent_rule():
    v1 = spec_v2_to_v1(load_spec(SPEC_DIR / "update_employee.json"))
    unskipped = {i.name for i in v1.policy_items if not i.skip}

    assert "Salary must be positive when set or updated" in unskipped
    assert "Editing an employee record is limited to self or HR" not in unskipped


def test_specs_for_unknown_tools_are_dropped():
    # gen_py would otherwise try to generate a guard for a tool that does not
    # exist (this is how a `global`-style spec used to leak through).
    specs = [_spec(_item()), SpecV2(tool_name="global", policy_items=[_item()])]

    converted = specs_v2_to_v1(specs, known_tools=["update_employee"])

    assert [s.tool_name for s in converted] == ["update_employee"]


def test_all_tools_are_kept_when_no_tool_list_is_given():
    specs = [_spec(_item()), SpecV2(tool_name="other", policy_items=[_item()])]

    assert len(specs_v2_to_v1(specs)) == 2
