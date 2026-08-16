"""Making every reference an exact substring of the policy document.

The spec schema requires each policy item to quote ``source_doc`` verbatim, and
the benchmark validator checks it by searching the document for each reference.
Models do not reliably comply: they paraphrase, drop markdown emphasis, change
case, or run two rules together. This module repairs what it can,
deterministically, and reports what it cannot.

Repair is attempted in order: an exact (or case-differing) substring is kept as
the document spells it; a near miss snaps to the closest bullet-level rule,
whose text is itself a verbatim slice; a reference that turns out to be two
quotes concatenated is split into both. Anything still unmatched is dropped, and
an item left with no reference at all is reported to the caller -- ``references``
is ``minItems: 1``, so such an item cannot be written.
"""

from __future__ import annotations

import difflib
from typing import List, Sequence

from loguru import logger

from toolguard.buildtime.gen_spec.utils import split_reference_if_both_parts_exist
from toolguard.buildtime.gen_spec_v2.data_types import PolicyItemV2
from toolguard.buildtime.gen_spec_v2.inputs import PolicyRule

#: Minimum SequenceMatcher ratio for a paraphrase to snap onto a rule.
DEFAULT_THRESHOLD = 0.6


def _substring_as_written(reference: str, policy_document: str) -> str | None:
    """The document's own spelling of ``reference``, if it appears at all.

    Matching ignores case; the returned slice keeps the document's casing, so
    the result is an exact substring even when the quote was not.
    """
    start = policy_document.lower().find(reference.lower())
    if start == -1:
        return None
    return policy_document[start : start + len(reference)]


def _closest_rule(
    reference: str, policy_rules: Sequence[PolicyRule], threshold: float
) -> str | None:
    """The closest rule's verbatim text, when it is close enough.

    Whitespace and case are normalized for the comparison only -- never in what
    is returned.
    """
    normalized = reference.strip().lower()
    best_text: str | None = None
    best_ratio = 0.0
    for rule in policy_rules:
        ratio = difflib.SequenceMatcher(
            None, normalized, rule.text.strip().lower()
        ).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_text = rule.text
    if best_text is not None and best_ratio >= threshold:
        return best_text
    return None


def repair_reference(
    reference: str,
    policy_document: str,
    policy_rules: Sequence[PolicyRule],
    threshold: float = DEFAULT_THRESHOLD,
) -> List[str]:
    """Repair one reference into zero, one, or two verbatim document quotes."""
    as_written = _substring_as_written(reference, policy_document)
    if as_written is not None:
        return [as_written]

    # Splitting is tried before snapping: two rules quoted as one string are
    # close enough to the first of them to snap, which would silently discard
    # the second. A split only succeeds when BOTH halves appear verbatim, so it
    # does not fire on a mere paraphrase.
    parts = split_reference_if_both_parts_exist(reference, policy_document)
    if parts:
        return list(parts)

    snapped = _closest_rule(reference, policy_rules, threshold)
    if snapped is not None:
        return [snapped]

    logger.warning(f"Dropping reference absent from the policy document: {reference!r}")
    return []


def repair_references(
    items: Sequence[PolicyItemV2],
    policy_document: str,
    policy_rules: Sequence[PolicyRule],
    threshold: float = DEFAULT_THRESHOLD,
) -> List[PolicyItemV2]:
    """Repair every item's references in place; return the items left with none.

    Duplicates that arise from two paraphrases of the same rule are collapsed,
    first occurrence winning. The returned items cannot be written -- the caller
    rejects them.
    """
    emptied: List[PolicyItemV2] = []
    for item in items:
        repaired: List[str] = []
        for reference in item.references:
            for candidate in repair_reference(
                reference, policy_document, policy_rules, threshold
            ):
                if candidate not in repaired:
                    repaired.append(candidate)
        item.references = repaired
        if not repaired:
            emptied.append(item)
    return emptied
