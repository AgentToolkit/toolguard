"""Reference repair: every reference must end up an exact substring of the doc."""

from toolguard.buildtime.gen_spec_v2.data_types import PolicyItemV2
from toolguard.buildtime.gen_spec_v2.inputs import extract_policy_rules
from toolguard.buildtime.gen_spec_v2.refmatch import (
    repair_reference,
    repair_references,
)

DOC = (
    "## Data Access\n"
    "\n"
    "- An employee may view and edit only their **own data**.\n"
    "- **HR** may view and edit all employees' data.\n"
    "- A single time-off request may not span more than **90 consecutive calendar days**.\n"
)
RULES = extract_policy_rules(DOC)


def test_an_exact_substring_is_left_untouched():
    ref = "**HR** may view and edit all employees' data."
    assert repair_reference(ref, DOC, RULES) == [ref]


def test_a_case_differing_quote_is_rewritten_to_the_documents_casing():
    got = repair_reference("**hr** MAY VIEW and edit all employees' data.", DOC, RULES)
    assert got == ["**HR** may view and edit all employees' data."]
    assert got[0] in DOC


def test_a_paraphrase_snaps_to_the_verbatim_rule():
    got = repair_reference("HR may view and edit the data of all employees", DOC, RULES)
    assert got == ["**HR** may view and edit all employees' data."]
    assert got[0] in DOC


def test_a_partial_quote_missing_markup_snaps_to_the_full_rule():
    got = repair_reference(
        "A single time-off request may not span more than 90 consecutive calendar days.",
        DOC,
        RULES,
    )
    assert got == [
        "A single time-off request may not span more than **90 consecutive calendar days**."
    ]


def test_two_rules_quoted_as_one_reference_split_into_both():
    concatenated = (
        "An employee may view and edit only their **own data**. "
        "**HR** may view and edit all employees' data."
    )
    got = repair_reference(concatenated, DOC, RULES)
    assert got == [
        "An employee may view and edit only their **own data**.",
        "**HR** may view and edit all employees' data.",
    ]
    assert all(part in DOC for part in got)


def test_two_rules_run_together_without_a_separator_fall_back_to_snapping():
    """The split heuristic works word-wise, so it cannot see a break mid-word.

    Documents the limitation rather than pretending it away: such a reference
    snaps to the closest single rule and the second quote is lost.
    """
    run_together = (
        "An employee may view and edit only their **own data**."
        "**HR** may view and edit all employees' data."
    )
    got = repair_reference(run_together, DOC, RULES)
    assert got == ["An employee may view and edit only their **own data**."]


def test_an_unmatchable_reference_is_dropped():
    assert (
        repair_reference("Flights may not exceed three passengers.", DOC, RULES) == []
    )


def test_repair_rewrites_items_in_place():
    item = PolicyItemV2(
        id="get_employee.hr_all",
        name="n",
        description="d",
        references=["HR may view and edit the data of all employees"],
    )
    repair_references([item], DOC, RULES)
    assert item.references == ["**HR** may view and edit all employees' data."]


def test_repair_reports_items_left_without_any_reference():
    grounded = PolicyItemV2(
        id="get_employee.hr_all",
        name="n",
        description="d",
        references=["**HR** may view and edit all employees' data."],
    )
    ungrounded = PolicyItemV2(
        id="get_employee.invented",
        name="n",
        description="d",
        references=["Flights may not exceed three passengers."],
    )
    emptied = repair_references([grounded, ungrounded], DOC, RULES)
    assert [item.id for item in emptied] == ["get_employee.invented"]
    assert ungrounded.references == []


def test_repair_deduplicates_references_that_snap_to_the_same_rule():
    item = PolicyItemV2(
        id="get_employee.hr_all",
        name="n",
        description="d",
        references=[
            "HR may view and edit the data of all employees",
            "**HR** may view and edit all employees' data.",
        ],
    )
    repair_references([item], DOC, RULES)
    assert item.references == ["**HR** may view and edit all employees' data."]


def test_repair_is_a_no_op_when_the_document_has_no_rules():
    ref = "**HR** may view and edit all employees' data."
    item = PolicyItemV2(id="t.a", name="n", description="d", references=[ref])
    assert repair_references([item], "", []) == [item]
    assert item.references == []
