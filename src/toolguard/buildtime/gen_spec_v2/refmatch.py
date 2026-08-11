"""Grounding quoted references back onto the policy document.

A reference is the evidence for a policy item: the span of the document the
item came from. The LLM quotes it, and quotes drift — line wrapping, dropped
markdown emphasis, a hyphen for an em-dash, a fragment instead of the whole
rule. This module maps a drifted quote back onto the exact original text, or
reports that it cannot.

Design notes, each replacing a defect in v1's ``find_mismatched_references``:

- :func:`normalize` returns an offset map alongside the normalized text, so a
  match can always be projected back to an exact original substring. v1 added
  the *reference's* length to a normalized index, which is only correct while
  normalization preserves length.
- Matching is against document *segments* (bullets, sentences), so a partial
  match snaps out to the whole rule instead of returning a fragment.
- The fallback requires **consecutive** segments, where v1 accepted any two
  fragments found anywhere in the document.
- A quote that cannot be grounded is reported, not silently kept.
"""

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Dict, List, Tuple

from loguru import logger
from pydantic import BaseModel

from toolguard.buildtime.gen_spec_v2.models import SpecV2

FUZZY_THRESHOLD = 0.75
"""Minimum SequenceMatcher ratio for a quote to be considered the same rule."""

SNAP_COVERAGE = 0.6
"""Fraction of a segment a match must cover before it snaps out to the whole segment."""

MAX_SPAN_SEGMENTS = 4
"""Longest run of consecutive segments a single quote may be grounded to."""

_DASHES = "‐‑‒–—―−"
_SINGLE_QUOTES = "‘’‚‛′"
_DOUBLE_QUOTES = "“”„‟″"
_DROPPED = "*_`~"
"""Markdown emphasis and code markers, dropped on both sides of a comparison."""

_BULLET = re.compile(r"^(\s*[-*+]\s+)(.*\S)\s*$")
_HEADING = re.compile(r"^\s*#{1,6}\s")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


class Span(BaseModel):
    """A stretch of the original document, with its exact text."""

    start: int
    end: int
    text: str


def normalize(text: str) -> Tuple[str, List[int]]:
    """Normalize ``text`` for comparison and map each output char to its source.

    Casefolds, unifies dashes and quotes, drops markdown emphasis, and
    collapses whitespace runs to a single space. ``offsets[i]`` is the index in
    ``text`` that produced ``norm[i]``, so any match on the normalized string
    projects back onto an exact original substring.
    """
    out: List[str] = []
    offsets: List[int] = []
    pending_space = False

    for index, char in enumerate(text):
        if char.isspace():
            pending_space = bool(out)
            continue

        if char in _DROPPED:
            continue

        if pending_space:
            out.append(" ")
            offsets.append(index)
            pending_space = False

        if char in _DASHES:
            replacement = "-"
        elif char in _SINGLE_QUOTES:
            replacement = "'"
        elif char in _DOUBLE_QUOTES:
            replacement = '"'
        else:
            replacement = unicodedata.normalize("NFKC", char).lower()

        for out_char in replacement:
            out.append(out_char)
            offsets.append(index)

    return "".join(out), offsets


def _norm(text: str) -> str:
    return normalize(text)[0]


def segments(doc: str) -> List[Span]:
    """Split ``doc`` into candidate reference units, with original spans.

    A markdown bullet is one unit with its marker excluded, since that is how
    a rule reads as a quote. Other prose is split into sentences. Headings and
    blank lines yield no units: nothing quotes them as a rule.
    """
    spans: List[Span] = []
    offset = 0

    for line in doc.splitlines(keepends=True):
        stripped = line.strip()
        if not stripped or _HEADING.match(line):
            offset += len(line)
            continue

        bullet = _BULLET.match(line.rstrip("\n"))
        if bullet:
            start = offset + len(bullet.group(1))
            text = bullet.group(2)
            spans.append(Span(start=start, end=start + len(text), text=text))
            offset += len(line)
            continue

        # Prose: one span per sentence, positioned within the line.
        line_body = line.rstrip("\n")
        indent = len(line_body) - len(line_body.lstrip())
        cursor = offset + indent
        for sentence in _SENTENCE_END.split(line_body.strip()):
            if not sentence:
                continue
            start = doc.find(sentence, cursor)
            if start < 0:
                continue
            spans.append(Span(start=start, end=start + len(sentence), text=sentence))
            cursor = start + len(sentence)
        offset += len(line)

    return spans


def _overlapping(spans: List[Span], start: int, end: int) -> List[Span]:
    return [s for s in spans if s.start < end and start < s.end]


def _exact(reference: str, doc: str, spans: List[Span]) -> List[str]:
    """Exact normalized substring match, snapped out to whole segments."""
    norm_doc, offsets = normalize(doc)
    norm_ref = _norm(reference)
    if not norm_ref:
        return []

    index = norm_doc.find(norm_ref)
    if index < 0:
        return []

    start = offsets[index]
    end = offsets[index + len(norm_ref) - 1] + 1
    touched = _overlapping(spans, start, end)

    if len(touched) > 1:
        return [s.text for s in touched]

    if touched:
        segment = touched[0]
        covered = min(end, segment.end) - max(start, segment.start)
        if covered >= SNAP_COVERAGE * (segment.end - segment.start):
            return [segment.text]

    return [doc[start:end]]


def _best_segment(norm_ref: str, spans: List[Span]) -> List[str]:
    """The single segment most similar to the quote, if similar enough."""
    best_ratio = 0.0
    best: List[str] = []
    for segment in spans:
        ratio = SequenceMatcher(None, norm_ref, _norm(segment.text)).ratio()
        if ratio > best_ratio:
            best_ratio, best = ratio, [segment.text]
    return best if best_ratio >= FUZZY_THRESHOLD else []


def _best_run(norm_ref: str, spans: List[Span]) -> List[str]:
    """The best run of consecutive segments, for a quote spanning a boundary."""
    best_ratio = 0.0
    best: List[str] = []
    for size in range(2, MAX_SPAN_SEGMENTS + 1):
        for i in range(len(spans) - size + 1):
            run = spans[i : i + size]
            joined = _norm(" ".join(s.text for s in run))
            ratio = SequenceMatcher(None, norm_ref, joined).ratio()
            if ratio > best_ratio:
                best_ratio, best = ratio, [s.text for s in run]
    return best if best_ratio >= FUZZY_THRESHOLD else []


def ground(reference: str, doc: str) -> List[str]:
    """Return the document spans ``reference`` quotes, or ``[]`` if none.

    Tries an exact normalized match first, then the closest single segment,
    then the closest run of consecutive segments. More than one span comes
    back when the quote genuinely crosses a segment boundary.
    """
    spans = segments(doc)
    if not spans:
        return []

    exact = _exact(reference, doc, spans)
    if exact:
        return exact

    norm_ref = _norm(reference)
    if not norm_ref:
        return []

    return _best_segment(norm_ref, spans) or _best_run(norm_ref, spans)


def ground_spec(spec: SpecV2, policy_text: str) -> List[str]:
    """Rewrite every item's references to verbatim spans of ``policy_text``.

    Grounded quotes are replaced (deduped, first-seen order). An item that keeps
    at least one grounded quote survives with its ungrounded ones intact —
    dropping those would weaken an otherwise sound item — but they are logged and
    recorded in ``spec.debug.notes`` so they are never mistaken for real
    citations.

    An item where **nothing** grounded is archived instead of kept. Every quote
    being absent from the policy document means the item is not a rule from this
    policy: in practice it has quoted a tool's own description. Keeping it would
    put a rule nobody wrote into the spec.

    Returns every ungrounded quote, from surviving and archived items alike.
    """
    ungrounded: List[str] = []
    per_item: Dict[str, List[str]] = {}
    kept = []

    for item in spec.policy_items:
        resolved: List[str] = []
        item_ungrounded: List[str] = []
        grounded_any = False

        for reference in item.references:
            spans = ground(reference, policy_text)
            if not spans:
                item_ungrounded.append(reference)
                if reference not in resolved:
                    resolved.append(reference)
                continue
            grounded_any = True
            for text in spans:
                if text not in resolved:
                    resolved.append(text)

        item.references = resolved
        if item_ungrounded:
            ungrounded.extend(item_ungrounded)

        if item.references and not grounded_any:
            logger.warning(
                "{}: archived — none of its {} reference(s) appear in the policy "
                "document",
                item.id,
                len(item.references),
            )
            spec.debug.archive.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "reason": (
                        "No reference could be located in the policy document, so the "
                        "item is not grounded in this policy."
                    ),
                    "stage": "refmatch",
                    "references": list(item.references),
                }
            )
            continue

        if item_ungrounded:
            per_item[item.id] = item_ungrounded
            logger.warning(
                "{}: {} reference(s) could not be grounded in the policy document",
                item.id,
                len(item_ungrounded),
            )
        kept.append(item)

    spec.policy_items = kept

    if per_item:
        notes = list(spec.debug.notes or [])
        notes.append({"stage": "refmatch", "ungrounded_references": per_item})
        spec.debug.notes = notes

    return ungrounded
