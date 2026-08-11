"""Combining several enrich votes into one answer.

The enrich stage asks the model the same question N times and reconciles the
answers here. The rules are deliberately asymmetric: a missing requirement
is worse than a spurious one, so `system_vars` unions while
`message_history` needs a majority.
"""

from toolguard.buildtime.gen_spec_v2.models import PendingType, Trigger
from toolguard.buildtime.gen_spec_v2.reconcile import reconcile


def vote(
    trigger="pre_tool",
    system_vars=None,
    tool_history=None,
    message_history=None,
    references=None,
    pending=None,
):
    return {
        "trigger": trigger,
        "requires": {
            "system_vars": system_vars or [],
            "tool_history": tool_history,
            "message_history": message_history,
        },
        "references": references or [],
        "pending_for_user": pending or [],
    }


# --- trigger ---------------------------------------------------------------


def test_majority_trigger_wins():
    result = reconcile([vote(trigger="post_tool")] * 2 + [vote()])

    assert result.trigger == Trigger.post_tool


def test_tied_trigger_resolves_to_pre_tool():
    # A pre-tool guard that should have been post-tool blocks a call; the
    # reverse lets one through. On a tie, prefer blocking.
    result = reconcile([vote(), vote(trigger="post_tool")])

    assert result.trigger == Trigger.pre_tool


def test_no_votes_yields_pre_tool_and_empty_requirements():
    result = reconcile([])

    assert result.trigger == Trigger.pre_tool
    assert result.requires.system_vars == []
    assert result.requires.tool_history is None
    assert result.requires.message_history is None


# --- system_vars -----------------------------------------------------------


def test_system_vars_are_the_sorted_union_of_every_vote():
    result = reconcile(
        [vote(system_vars=["user_id"]), vote(system_vars=["department", "user_id"])]
    )

    assert result.requires.system_vars == ["department", "user_id"]


# --- tool_history ----------------------------------------------------------


def test_tool_history_is_none_when_a_strict_majority_say_none():
    history = [
        {"tool": "get_employee", "params": {"user_id": "input.arguments.user_id"}}
    ]
    result = reconcile([vote(), vote(), vote(tool_history=history)])

    assert result.requires.tool_history is None


def test_longest_tool_history_wins_when_the_majority_want_one():
    short = [{"tool": "get_employee", "params": {}}]
    long = [
        {"tool": "get_employee", "params": {}},
        {"tool": "get_leave_balance", "params": {"year": "2026"}},
    ]
    result = reconcile([vote(tool_history=short), vote(tool_history=long), vote()])

    assert result.requires.tool_history is not None
    assert [e.tool for e in result.requires.tool_history] == [
        "get_employee",
        "get_leave_balance",
    ]


def test_tool_history_params_survive_reconciliation():
    history = [
        {"tool": "get_employee", "params": {"user_id": "input.arguments.user_id"}}
    ]
    result = reconcile([vote(tool_history=history), vote(tool_history=history)])

    assert result.requires.tool_history is not None
    assert result.requires.tool_history[0].params == {
        "user_id": "input.arguments.user_id"
    }


# --- message_history -------------------------------------------------------


def test_message_history_needs_a_strict_majority():
    assert (
        reconcile([vote(message_history=True), vote(), vote()]).requires.message_history
        is None
    )


def test_message_history_is_true_on_a_majority():
    result = reconcile([vote(message_history=True)] * 2 + [vote()])

    assert result.requires.message_history is True


def test_message_history_is_none_rather_than_false_when_unneeded():
    # The on-disk format uses null, not false, for "not needed".
    assert reconcile([vote(), vote()]).requires.message_history is None


# --- references ------------------------------------------------------------


def test_references_union_in_first_seen_order():
    result = reconcile([vote(references=["b", "a"]), vote(references=["a", "c"])])

    assert result.references == ["b", "a", "c"]


# --- pending_for_user ------------------------------------------------------


def _pending(type_="missing_tool", question="which tool?", detail="d"):
    return {"type": type_, "detail": detail, "question": question}


def test_pending_entries_dedupe_by_type_and_question():
    result = reconcile([vote(pending=[_pending()]), vote(pending=[_pending()])])

    assert len(result.pending_for_user) == 1
    assert result.pending_for_user[0].type == PendingType.missing_tool


def test_pending_entries_differing_in_question_are_both_kept():
    result = reconcile(
        [
            vote(pending=[_pending(question="which tool?")]),
            vote(pending=[_pending(question="add one?")]),
        ]
    )

    assert len(result.pending_for_user) == 2


def test_pending_type_alias_is_normalized():
    result = reconcile([vote(pending=[_pending(type_="missing_variable")])])

    assert result.pending_for_user[0].type == PendingType.missing_var


def test_pending_entry_with_an_unknown_type_is_dropped():
    result = reconcile([vote(pending=[_pending(type_="vibes")])])

    assert result.pending_for_user == []


def test_pending_entry_missing_a_question_is_dropped():
    result = reconcile([vote(pending=[{"type": "missing_tool", "detail": "d"}])])

    assert result.pending_for_user == []


# --- malformed votes -------------------------------------------------------


def test_a_vote_missing_every_key_is_tolerated():
    result = reconcile([{}, vote(system_vars=["user_id"])])

    assert result.requires.system_vars == ["user_id"]
    assert result.trigger == Trigger.pre_tool


def test_a_non_dict_vote_is_ignored():
    result = reconcile(["nonsense", vote(trigger="post_tool")])

    assert result.trigger == Trigger.post_tool


def test_a_vote_with_a_malformed_requires_is_tolerated():
    result = reconcile([{"trigger": "pre_tool", "requires": None}, vote()])

    assert result.requires.system_vars == []
