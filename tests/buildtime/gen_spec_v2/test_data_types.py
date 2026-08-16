"""Schema fidelity of the step1 spec models.

The contract these tests defend is `step1.schema.json`, vendored next to them
from the benchmark repo. The tricky part is not the field list but which keys
must vanish when empty (`conflicts`, `pending_for_user`, `resolved_by_user`),
which must stay even when empty (`system_vars`, `tool_history`), and which must
stay as an explicit null or false (`message_history`, a conflict's `resolution`).
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from toolguard.buildtime.gen_spec_v2.data_types import (
    Conflict,
    PendingItem,
    PolicyItemV2,
    Requires,
    Resolution,
    ResolvedItem,
    ToolGuardSpecV2,
    ToolHistoryEntry,
    dump_spec,
    load_spec,
    slugify,
    unique_id,
)

SCHEMA_PATH = Path(__file__).parent / "step1.schema.json"


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def minimal_item(item_id: str = "get_bank_account.read_own") -> PolicyItemV2:
    return PolicyItemV2(
        id=item_id,
        name="Bank-account read limited to self",
        description="A user may read only their own bank account.",
        compliance_examples=["A user reads their own bank account."],
        violation_examples=["A user reads a colleague's bank account."],
        references=["An employee may view and edit only their **own data**"],
        trigger="pre_tool",
        requires=Requires(system_vars=["user_id"]),
    )


def minimal_spec(**kwargs) -> ToolGuardSpecV2:
    return ToolGuardSpecV2(
        tool_name="get_bank_account",
        source_doc="benchmarks/employee/inputs/employee_policy_doc.md",
        policy_items=[minimal_item()],
        **kwargs,
    )


def test_spec_emits_schema_key_order():
    d = minimal_spec().to_dict()
    assert list(d) == ["tool_name", "source_doc", "policy_items"]


def test_item_emits_schema_key_order():
    d = minimal_spec().to_dict()
    assert list(d["policy_items"][0]) == [
        "id",
        "name",
        "description",
        "compliance_examples",
        "violation_examples",
        "references",
        "trigger",
        "requires",
    ]


def test_requires_keeps_empty_values_rather_than_nulls():
    d = minimal_spec().to_dict()
    requires = d["policy_items"][0]["requires"]
    assert requires == {
        "system_vars": ["user_id"],
        "tool_history": [],
        "message_history": False,
    }


def test_tool_history_entry_is_emitted_in_full():
    item = minimal_item()
    item.requires.tool_history = [
        ToolHistoryEntry(
            tool="get_direct_reports",
            params={"user_id": "input.extensions.subject.user_id"},
        )
    ]
    d = ToolGuardSpecV2(
        tool_name="get_bank_account", source_doc="doc.md", policy_items=[item]
    ).to_dict()
    assert d["policy_items"][0]["requires"]["tool_history"] == [
        {
            "tool": "get_direct_reports",
            "params": {"user_id": "input.extensions.subject.user_id"},
        }
    ]


def test_empty_conflicts_key_is_omitted():
    assert "conflicts" not in minimal_spec(conflicts=[]).to_dict()


def test_empty_pending_and_resolved_keys_are_omitted():
    item = minimal_spec().to_dict()["policy_items"][0]
    assert "pending_for_user" not in item
    assert "resolved_by_user" not in item


def test_pending_missing_variable_emits_only_suggested_source():
    item = minimal_item()
    item.pending_for_user = [
        PendingItem(
            type="missing_variable",
            detail="No blacklist signal exists.",
            question="How does the policy learn whether an employee is blacklisted?",
            suggested_source="system_vars.json:blacklist",
        )
    ]
    d = ToolGuardSpecV2(
        tool_name="update_passport", source_doc="doc.md", policy_items=[item]
    ).to_dict()
    pending = d["policy_items"][0]["pending_for_user"][0]
    assert list(pending) == ["type", "detail", "suggested_source", "question"]


def test_pending_missing_tool_emits_only_suggested_tool():
    item = minimal_item()
    item.pending_for_user = [
        PendingItem(
            type="missing_tool",
            detail="No notification tool exists.",
            question="Which tool should send the manager approval email?",
            suggested_tool="send_email",
        )
    ]
    d = ToolGuardSpecV2(
        tool_name="create_time_off_request", source_doc="doc.md", policy_items=[item]
    ).to_dict()
    pending = d["policy_items"][0]["pending_for_user"][0]
    assert list(pending) == ["type", "detail", "suggested_tool", "question"]


def test_pending_clarification_emits_neither_suggestion():
    item = minimal_item()
    item.pending_for_user = [
        PendingItem(
            type="clarification",
            detail="'same area' is undefined.",
            question="What counts as the same area?",
        )
    ]
    d = ToolGuardSpecV2(
        tool_name="set_emergency_contact", source_doc="doc.md", policy_items=[item]
    ).to_dict()
    pending = d["policy_items"][0]["pending_for_user"][0]
    assert list(pending) == ["type", "detail", "question"]


def test_resolved_item_emits_resolution_last():
    item = minimal_item()
    item.resolved_by_user = [
        ResolvedItem(
            type="clarification",
            detail="Does the rule bind HR?",
            question="Does the own-data rule bind HR editing others?",
            resolution=Resolution(
                answer="HR is exempt.",
                decided_by="human",
                effect="Description now exempts HR.",
            ),
        )
    ]
    d = ToolGuardSpecV2(
        tool_name="update_employee", source_doc="doc.md", policy_items=[item]
    ).to_dict()
    resolved = d["policy_items"][0]["resolved_by_user"][0]
    assert list(resolved) == ["type", "detail", "question", "resolution"]
    assert list(resolved["resolution"]) == ["answer", "decided_by", "effect"]


def test_conflict_emits_null_resolution():
    conflict = Conflict(
        id="conflict.update_employee.home_address_scope_vs_hr",
        name="Does the in-country rule bind HR?",
        kind="scope",
        conflicting_policies=[
            "update_employee.edit_own_or_hr",
            "update_employee.home_address_same_country",
        ],
        description="Applies when HR relocates an employee across countries.",
        question="Does the home-address rule bind HR?",
    )
    d = minimal_spec(conflicts=[conflict]).to_dict()
    assert list(d) == ["tool_name", "source_doc", "policy_items", "conflicts"]
    assert list(d["conflicts"][0]) == [
        "id",
        "name",
        "kind",
        "conflicting_policies",
        "description",
        "question",
        "resolution",
    ]
    assert d["conflicts"][0]["resolution"] is None


def test_skip_field_is_never_emitted():
    """v2 leaves `skip` to the later v2 -> v1 adapter."""
    assert "skip" not in minimal_spec().to_dict()["policy_items"][0]


def test_minimal_spec_validates_against_vendored_schema(validator):
    assert not list(validator.iter_errors(minimal_spec().to_dict()))


def test_fully_populated_spec_validates_against_vendored_schema(validator):
    item = minimal_item()
    item.requires = Requires(
        system_vars=["user_id", "department"],
        tool_history=[
            ToolHistoryEntry(
                tool="get_leave_balance",
                params={"year": "year-of(input.arguments.start_date)"},
            )
        ],
        message_history=True,
    )
    item.pending_for_user = [
        PendingItem(
            type="missing_tool",
            detail="No notification tool exists.",
            question="Which tool sends the email?",
            suggested_tool="send_email",
        )
    ]
    second = minimal_item("get_bank_account.outside_ibm")
    second.resolved_by_user = [
        ResolvedItem(
            type="clarification",
            detail="Ambiguous org definition.",
            question="What counts as IBM?",
            resolution=Resolution(
                answer="IBM Corporation only.", decided_by="human", effect="Narrowed."
            ),
        )
    ]
    spec = ToolGuardSpecV2(
        tool_name="get_bank_account",
        source_doc="doc.md",
        policy_items=[item, second],
        conflicts=[
            Conflict(
                id="conflict.get_bank_account.ibm_organization_definition",
                name="What counts as the IBM organization?",
                kind="definition",
                conflicting_policies=[
                    "get_bank_account.read_own",
                    "get_bank_account.outside_ibm",
                ],
                description="Both rules lean on an undefined term.",
                question="Which organizations count as IBM?",
            )
        ],
    )
    assert not list(validator.iter_errors(spec.to_dict()))


def test_round_trip_through_disk_preserves_the_spec(tmp_path):
    spec = minimal_spec(
        conflicts=[
            Conflict(
                id="conflict.get_bank_account.x_vs_y",
                name="n",
                kind="scope",
                conflicting_policies=["get_bank_account.a", "get_bank_account.b"],
                description="d",
                question="q",
            )
        ]
    )
    spec.policy_items[0].pending_for_user = [
        PendingItem(
            type="missing_variable",
            detail="d",
            question="q",
            suggested_source="s",
        )
    ]
    path = tmp_path / "get_bank_account.json"
    dump_spec(spec, path)
    assert load_spec(path).to_dict() == spec.to_dict()


def test_dump_writes_trailing_newline_and_two_space_indent(tmp_path):
    path = tmp_path / "get_bank_account.json"
    dump_spec(minimal_spec(), path)
    text = path.read_text(encoding="utf-8")
    assert text.endswith("}\n")
    assert '\n  "tool_name"' in text


def test_slugify_produces_only_schema_legal_characters():
    assert slugify("Read own data (self-service)!") == "read_own_data_self_service"


def test_unique_id_suffixes_until_unused():
    taken = {"t.a", "t.a_2"}
    assert unique_id("t", "a", taken) == "t.a_3"
    assert unique_id("t", "b", taken) == "t.b"
    assert taken == {"t.a", "t.a_2"}, "unique_id must not mutate the taken set"
