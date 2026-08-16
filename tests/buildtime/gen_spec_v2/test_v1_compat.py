"""Handing v2 specs to the v1 code generator: compute `skip`, keep everything else.

No conversion happens on disk. A v2 spec file already loads as a v1
`ToolGuardSpec` (pydantic drops the v2-only keys), so the only thing v1 needs
that v2 does not store is `skip` -- the flag `gen_py` uses to leave a rule out of
code generation. It is computed in memory, at the moment the specs are handed
over.
"""

from toolguard.buildtime.gen_spec_v2.data_types import (
    PendingItem,
    PolicyItemV2,
    Requires,
    ToolGuardSpecV2,
    ToolHistoryEntry,
)
from toolguard.buildtime.gen_spec_v2.v1_compat import (
    skip_for,
    skip_reasons,
    to_v1_spec,
    to_v1_specs,
)
from toolguard.runtime.data_types import ToolGuardSpec


def item(**kwargs) -> PolicyItemV2:
    defaults = dict(
        id="update_employee.edit_own",
        name="Editing is limited to self",
        description="A user may edit only their own record.",
        compliance_examples=["Bob edits his own record."],
        violation_examples=["Bob edits a colleague's record."],
        references=["An employee may view and edit only their **own data**"],
        trigger="pre_tool",
        requires=Requires(),
    )
    defaults.update(kwargs)
    return PolicyItemV2(**defaults)


# --- the skip predicate ------------------------------------------------------


def test_an_argument_only_rule_is_not_skipped():
    """Everything it needs is in the call itself, so gen_py can enforce it."""
    assert skip_for(item()) is False


def test_a_rule_needing_a_system_variable_is_skipped():
    assert skip_for(item(requires=Requires(system_vars=["user_id"]))) is True


def test_a_rule_needing_the_conversation_is_skipped():
    assert skip_for(item(requires=Requires(message_history=True))) is True


def test_a_post_tool_rule_is_skipped():
    assert skip_for(item(trigger="post_tool")) is True


def test_a_rule_with_an_open_question_is_skipped():
    pending = [PendingItem(type="clarification", detail="d", question="q?")]
    assert skip_for(item(pending_for_user=pending)) is True


def test_a_rule_needing_only_prior_tool_calls_is_not_skipped():
    """Generated guard code may call read-only app APIs, so history is fine."""
    history = [ToolHistoryEntry(tool="get_direct_reports", params={"user_id": "x"})]
    assert skip_for(item(requires=Requires(tool_history=history))) is False


def test_a_resolved_question_does_not_cause_a_skip():
    """resolved_by_user means a human already decided; the rule stands."""
    assert skip_for(item()) is False


def test_skip_reasons_names_every_reason_that_applies():
    reasons = skip_reasons(
        item(
            trigger="post_tool",
            requires=Requires(system_vars=["user_id"], message_history=True),
        )
    )
    assert sorted(reasons) == ["message_history", "post_tool", "system_vars"]


def test_skip_reasons_is_empty_for_an_enforceable_rule():
    assert skip_reasons(item()) == []


# --- the in-memory hand-over -------------------------------------------------


def spec_v2() -> ToolGuardSpecV2:
    return ToolGuardSpecV2(
        tool_name="update_employee",
        source_doc="inputs/policy_doc.md",
        policy_items=[
            item(),
            item(
                id="update_employee.salary_hr_only",
                name="Salary changes restricted to HR",
                requires=Requires(system_vars=["department"]),
            ),
        ],
    )


def test_to_v1_spec_produces_a_real_v1_spec():
    converted = to_v1_spec(spec_v2())
    assert isinstance(converted, ToolGuardSpec)
    assert converted.tool_name == "update_employee"
    assert [i.name for i in converted.policy_items] == [
        "Editing is limited to self",
        "Salary changes restricted to HR",
    ]


def test_the_v1_fields_carry_across_untouched():
    original = spec_v2()
    converted = to_v1_spec(original)
    for before, after in zip(original.policy_items, converted.policy_items):
        assert after.name == before.name
        assert after.description == before.description
        assert after.references == before.references
        assert after.compliance_examples == before.compliance_examples
        assert after.violation_examples == before.violation_examples


def test_skip_is_stamped_per_item():
    converted = to_v1_spec(spec_v2())
    assert [i.skip for i in converted.policy_items] == [False, True]


def test_gen_py_filtering_keeps_only_the_enforceable_items():
    """The contract gen_py relies on: `[i for i in policy_items if not i.skip]`."""
    converted = to_v1_spec(spec_v2())
    enforceable = [i for i in converted.policy_items if not i.skip]
    assert [i.name for i in enforceable] == ["Editing is limited to self"]


def test_the_v2_only_fields_are_preserved_in_debug():
    """Nothing is thrown away: v1 has no home for them, so debug carries them."""
    converted = to_v1_spec(spec_v2())
    provenance = converted.policy_items[1].debug["v2"]
    assert provenance["id"] == "update_employee.salary_hr_only"
    assert provenance["trigger"] == "pre_tool"
    assert provenance["requires"]["system_vars"] == ["department"]
    assert provenance["skip_reasons"] == ["system_vars"]


def test_the_v2_spec_is_not_mutated_by_the_hand_over():
    original = spec_v2()
    to_v1_spec(original)
    assert not hasattr(original.policy_items[0], "skip")
    assert "skip" not in original.to_dict()["policy_items"][0]


def test_to_v1_specs_converts_a_whole_run():
    other = ToolGuardSpecV2(
        tool_name="get_bank_account", source_doc="d.md", policy_items=[item()]
    )
    converted = to_v1_specs([spec_v2(), other])
    assert [s.tool_name for s in converted] == ["update_employee", "get_bank_account"]
