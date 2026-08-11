"""Grounding a quoted reference back onto the policy document.

Each test here corresponds to a way v1's `find_mismatched_references` fails:
lowercase-only normalization, offset projection that assumes normalization
preserves length, a two-part split that accepts unrelated fragments, and no
fuzzy matching at all.
"""

from toolguard.buildtime.gen_spec_v2.models import PolicyItemV2, SpecV2
from toolguard.buildtime.gen_spec_v2.refmatch import (
    ground,
    ground_spec,
    normalize,
    segments,
)

POLICY = """# Employee Hub Policy

## Data Access

- An employee may view and edit only their **own data** — home address, passport, visa, emergency contact, and bank account.
- **HR** may view and edit all employees' data.
- An employee's `salary` may be updated only by **HR** or by that employee's **direct manager**.

## Confirmation

- A user may be deleted only after the requester provides explicit confirmation in exactly this form:
  `I request to delete user [USER NAME] with the following user id: [USER ID]`.

The agent must be careful. It should never guess an identity. Ambiguity is resolved by asking.
"""

HR_RULE = "**HR** may view and edit all employees' data."


# --- normalize -------------------------------------------------------------


def test_normalize_maps_every_output_char_back_to_its_source():
    text = "A  **B**\nC"
    norm, offsets = normalize(text)

    assert len(offsets) == len(norm)
    # Every offset points at the character it came from.
    for i, char in enumerate(norm):
        if char != " ":
            assert text[offsets[i]].lower() == char


def test_normalize_collapses_whitespace_and_drops_emphasis():
    norm, _ = normalize("**HR**   may\n  edit")

    assert norm == "hr may edit"


def test_normalize_unifies_dashes():
    assert normalize("a — b")[0] == normalize("a - b")[0]


# --- segments --------------------------------------------------------------


def test_bullet_segments_exclude_the_list_marker():
    texts = [s.text for s in segments(POLICY)]

    assert HR_RULE in texts


def test_prose_is_split_into_sentences():
    texts = [s.text for s in segments(POLICY)]

    assert "It should never guess an identity." in texts


def test_segment_spans_point_at_the_original_text():
    for segment in segments(POLICY):
        assert POLICY[segment.start : segment.end] == segment.text


# --- ground ----------------------------------------------------------------


def test_exact_quote_grounds_to_itself():
    assert ground(HR_RULE, POLICY) == [HR_RULE]


def test_line_wrapped_quote_grounds():
    wrapped = "**HR** may view and\n     edit all employees' data."

    assert ground(wrapped, POLICY) == [HR_RULE]


def test_quote_with_markdown_stripped_grounds_to_the_marked_up_original():
    assert ground("HR may view and edit all employees' data.", POLICY) == [HR_RULE]


def test_quote_with_a_hyphen_grounds_to_the_em_dash_original():
    quote = (
        "An employee may view and edit only their **own data** - home address, "
        "passport, visa, emergency contact, and bank account."
    )

    grounded = ground(quote, POLICY)

    assert len(grounded) == 1
    assert "—" in grounded[0]


def test_mid_sentence_fragment_snaps_out_to_the_whole_rule():
    # v1 would return the bare fragment; a reference should be a whole rule.
    assert ground("may view and edit all employees' data", POLICY) == [HR_RULE]


def test_paraphrase_grounds_to_the_closest_rule():
    quote = "An employee's salary may only be updated by HR or by the employee's direct manager."

    grounded = ground(quote, POLICY)

    assert len(grounded) == 1
    assert grounded[0].startswith("An employee's `salary` may be updated only by")


def test_quote_spanning_two_segments_returns_both():
    quote = (
        "A user may be deleted only after the requester provides explicit "
        "confirmation in exactly this form: `I request to delete user [USER NAME] "
        "with the following user id: [USER ID]`."
    )

    grounded = ground(quote, POLICY)

    assert len(grounded) == 2
    assert grounded[0].endswith("in exactly this form:")
    assert grounded[1].startswith("`I request to delete user")


def test_unrelated_quote_does_not_ground():
    assert ground("Passengers may check two bags on domestic flights.", POLICY) == []


def test_two_unrelated_fragments_are_not_stitched_together():
    # v1's fallback accepted any two halves found anywhere in the document.
    assert ground("employees' data bank account salary manager", POLICY) == []


# --- ground_spec -----------------------------------------------------------


def _spec(references) -> SpecV2:
    return SpecV2(
        tool_name="update_employee",
        policy_items=[
            PolicyItemV2(
                id="update_employee.x",
                name="x",
                description="d",
                references=references,
            )
        ],
    )


def test_ground_spec_rewrites_references_to_verbatim_spans():
    spec = _spec(["HR may view and edit all employees' data."])

    ungrounded = ground_spec(spec, POLICY)

    assert spec.policy_items[0].references == [HR_RULE]
    assert ungrounded == []
    assert spec.debug.notes is None


def test_ground_spec_dedupes_references_that_ground_to_one_rule():
    spec = _spec([HR_RULE, "may view and edit all employees' data"])

    ground_spec(spec, POLICY)

    assert spec.policy_items[0].references == [HR_RULE]


def test_ground_spec_keeps_an_ungrounded_reference_and_records_it():
    invented = "Employees must wear a badge at all times."
    spec = _spec([HR_RULE, invented])

    ungrounded = ground_spec(spec, POLICY)

    assert spec.policy_items[0].references == [HR_RULE, invented]
    assert ungrounded == [invented]
    assert spec.debug.notes is not None
    assert invented in str(spec.debug.notes)


def test_ground_spec_leaves_an_item_without_references_alone():
    spec = _spec([])

    assert ground_spec(spec, POLICY) == []
    assert spec.policy_items[0].references == []


def test_an_item_grounded_in_nothing_is_archived():
    # An item whose every quote is absent from the policy document is not a rule
    # from this policy at all — in practice it has quoted a tool's own docstring.
    # Keeping it would let a rule nobody wrote reach the spec.
    invented = "Only transfer if the user explicitly asks for a human agent."
    spec = _spec([invented])

    ungrounded = ground_spec(spec, POLICY)

    assert spec.policy_items == []
    assert ungrounded == [invented]
    entry = spec.debug.archive[0]
    assert entry["id"] == "update_employee.x"
    assert entry["stage"] == "refmatch"
    assert invented in entry["references"]
    assert "policy document" in entry["reason"]


def test_an_item_with_one_grounded_quote_survives():
    spec = _spec(["Employees must wear a badge.", HR_RULE])

    ground_spec(spec, POLICY)

    assert len(spec.policy_items) == 1
    assert spec.debug.archive == []


def test_only_the_ungrounded_item_is_archived():
    spec = SpecV2(
        tool_name="update_employee",
        policy_items=[
            PolicyItemV2(
                id="update_employee.good",
                name="g",
                description="d",
                references=[HR_RULE],
            ),
            PolicyItemV2(
                id="update_employee.bad",
                name="b",
                description="d",
                references=["Badges are mandatory."],
            ),
        ],
    )

    ground_spec(spec, POLICY)

    assert [i.id for i in spec.policy_items] == ["update_employee.good"]
    assert [a["id"] for a in spec.debug.archive] == ["update_employee.bad"]
