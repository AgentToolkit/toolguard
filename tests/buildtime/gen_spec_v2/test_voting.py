"""Vote reconciliation and tallying -- the pure logic behind enrich and review."""

from toolguard.buildtime.gen_spec_v2.stages.enrich import normalize_pending, reconcile
from toolguard.buildtime.gen_spec_v2.stages.review import tally


def vote(
    trigger="pre_tool",
    system_vars=None,
    tool_history=None,
    message_history=False,
    references=None,
    pending=None,
):
    return {
        "trigger": trigger,
        "requires": {
            "system_vars": system_vars if system_vars is not None else [],
            "tool_history": tool_history if tool_history is not None else [],
            "message_history": message_history,
        },
        "references": references if references is not None else [],
        "pending_for_user": pending if pending is not None else [],
    }


# --- trigger -----------------------------------------------------------------


def test_trigger_follows_the_majority():
    got = reconcile([vote(trigger="post_tool"), vote(trigger="post_tool"), vote()])
    assert got["trigger"] == "post_tool"


def test_a_tied_trigger_resolves_to_pre_tool():
    got = reconcile([vote(trigger="post_tool"), vote(trigger="pre_tool")])
    assert got["trigger"] == "pre_tool"


def test_an_unrecognized_trigger_does_not_win():
    got = reconcile([vote(trigger="whenever"), vote(trigger="whenever"), vote()])
    assert got["trigger"] == "pre_tool"


# --- requires ----------------------------------------------------------------


def test_system_vars_are_the_sorted_union_of_every_vote():
    got = reconcile(
        [vote(system_vars=["user_id", "department"]), vote(system_vars=["user_id"])]
    )
    assert got["requires"]["system_vars"] == ["department", "user_id"]


def test_tool_history_comes_from_the_vote_that_lists_the_most():
    rich = [
        {"tool": "get_employee", "params": {}},
        {"tool": "get_manager", "params": {}},
    ]
    got = reconcile(
        [
            vote(tool_history=rich),
            vote(tool_history=[{"tool": "get_employee", "params": {}}]),
            vote(tool_history=[{"tool": "get_employee", "params": {}}]),
        ]
    )
    assert got["requires"]["tool_history"] == rich


def test_tool_history_is_empty_when_a_strict_majority_says_none():
    got = reconcile(
        [vote(tool_history=[{"tool": "get_employee", "params": {}}]), vote(), vote()]
    )
    assert got["requires"]["tool_history"] == []


def test_message_history_needs_a_strict_majority():
    assert (
        reconcile([vote(message_history=True), vote(), vote()])["requires"][
            "message_history"
        ]
        is False
    )
    assert (
        reconcile([vote(message_history=True), vote(message_history=True), vote()])[
            "requires"
        ]["message_history"]
        is True
    )


def test_requires_never_reconciles_to_none():
    """ "Nothing needed" is the empty/false value; the schema forbids nulls here."""
    got = reconcile([vote()])["requires"]
    assert got == {"system_vars": [], "tool_history": [], "message_history": False}


def test_a_vote_missing_keys_is_tolerated():
    got = reconcile([{"trigger": "pre_tool"}, vote()])
    assert got["requires"] == {
        "system_vars": [],
        "tool_history": [],
        "message_history": False,
    }


# --- references --------------------------------------------------------------


def test_references_union_preserves_first_seen_order():
    got = reconcile([vote(references=["b", "a"]), vote(references=["a", "c"])])
    assert got["references"] == ["b", "a", "c"]


# --- pending_for_user --------------------------------------------------------


def test_pending_entries_are_deduped_by_type_and_question():
    entry = {"type": "clarification", "detail": "d", "question": "q?"}
    got = reconcile(
        [vote(pending=[entry]), vote(pending=[dict(entry, detail="other")])]
    )
    assert len(got["pending_for_user"]) == 1
    assert got["pending_for_user"][0]["detail"] == "d"


def test_normalize_keeps_a_well_formed_missing_variable_entry():
    entries = normalize_pending(
        [
            {
                "type": "missing_variable",
                "detail": "no blacklist signal",
                "question": "where from?",
                "suggested_source": "system_vars.json:blacklist",
            }
        ]
    )
    assert len(entries) == 1
    assert entries[0].type == "missing_variable"
    assert entries[0].suggested_source == "system_vars.json:blacklist"


def test_normalize_downgrades_missing_tool_without_a_suggested_tool():
    """The schema requires the companion key; we cannot invent a tool name."""
    entries = normalize_pending(
        [{"type": "missing_tool", "detail": "d", "question": "q?"}]
    )
    assert entries[0].type == "clarification"
    assert entries[0].suggested_tool is None
    assert entries[0].suggested_source is None


def test_normalize_downgrades_missing_variable_without_a_suggested_source():
    entries = normalize_pending(
        [{"type": "missing_variable", "detail": "d", "question": "q?"}]
    )
    assert entries[0].type == "clarification"


def test_normalize_strips_a_suggestion_the_type_forbids():
    entries = normalize_pending(
        [
            {
                "type": "missing_tool",
                "detail": "d",
                "question": "q?",
                "suggested_tool": "send_email",
                "suggested_source": "somewhere",
            }
        ]
    )
    assert entries[0].suggested_tool == "send_email"
    assert entries[0].suggested_source is None


def test_normalize_strips_both_suggestions_from_a_clarification():
    entries = normalize_pending(
        [
            {
                "type": "clarification",
                "detail": "d",
                "question": "q?",
                "suggested_tool": "send_email",
                "suggested_source": "somewhere",
            }
        ]
    )
    assert entries[0].suggested_tool is None
    assert entries[0].suggested_source is None


def test_normalize_drops_incomplete_and_unknown_entries():
    assert normalize_pending([{"type": "clarification", "detail": "d"}]) == []
    assert normalize_pending([{"detail": "d", "question": "q?"}]) == []
    assert normalize_pending(["not a dict"]) == []
    assert (
        normalize_pending([{"type": "made_up", "detail": "d", "question": "q?"}]) == []
    )


# --- review tally ------------------------------------------------------------


def test_an_item_is_kept_on_a_strict_majority_of_both_checks():
    keep, _ = tally(
        [
            {"is_relevant": True, "can_be_validated": True, "reason": "yes"},
            {"is_relevant": True, "can_be_validated": True, "reason": "yes"},
            {"is_relevant": False, "can_be_validated": True, "reason": "no"},
        ]
    )
    assert keep is True


def test_an_item_is_dropped_on_a_tie():
    keep, _ = tally(
        [
            {"is_relevant": True, "can_be_validated": True, "reason": "yes"},
            {"is_relevant": True, "can_be_validated": False, "reason": "cannot check"},
        ]
    )
    assert keep is False


def test_tally_joins_every_vote_reason():
    _, reason = tally(
        [
            {"is_relevant": False, "can_be_validated": True, "reason": "not this tool"},
            {"is_relevant": False, "can_be_validated": True, "reason": "orchestration"},
        ]
    )
    assert reason == "not this tool orchestration"


def test_tally_with_no_votes_drops_the_item():
    keep, reason = tally([])
    assert keep is False
    assert reason == ""


def test_tally_tolerates_a_vote_missing_keys():
    keep, _ = tally([{"is_relevant": True}, {"is_relevant": True}])
    assert keep is False
