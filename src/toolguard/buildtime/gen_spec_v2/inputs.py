"""Turning the two free-form inputs into normalized values.

The policy document arrives as markdown text and is split into atomic
bullet-level rules; ``sys_var`` arrives as a mapping (or a path to one) and is
filtered down to the variables that describe the acting user.

Every extracted rule is a verbatim slice of the document, offsets and all. That
is not incidental: the spec schema requires each policy item's ``references`` to
be an exact substring of ``source_doc``, so a rule text that "tidied up"
whitespace while joining a multi-line bullet would quote something the document
does not contain.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Union

from pydantic import BaseModel, Field

from toolguard.buildtime.gen_spec_v2.data_types import slugify

#: Keys of ``sys_var`` that describe the agent's action surface rather than the
#: acting user, so they are not policy inputs.
NON_SUBJECT_KEYS = ("action_list", "action_description")

_BULLET = re.compile(r"^(\s*)([-*])(\s+)(\S.*)$")
_HTML_MARKERS = ("</li>", "</p>", "</ul>", "</ol>")


class HtmlPolicyDocumentError(ValueError):
    """The policy document is rendered HTML; the markdown source is required.

    Rendered HTML is rejected rather than tolerated. Two things break with it:
    rules are found by their ``- ``/``* `` bullet markers, of which HTML has
    none, and every reference has to be quotable verbatim from ``source_doc`` --
    which names the markdown file, not a rendering of it. Accepting HTML would
    mean a run that costs a model call per tool and produces no specs at all.
    """


class PolicyRule(BaseModel):
    """One bullet-level rule, quoted verbatim from the policy document."""

    text: str
    slug: str


class SystemVars(BaseModel):
    """The acting user's variables, and which of them policy may read."""

    names: List[str] = Field(default_factory=list)
    raw: Dict[str, Any] = Field(default_factory=dict)


def looks_like_html(text: str) -> bool:
    """True when ``text`` appears to be rendered HTML rather than markdown.

    Callers pass the policy document as markdown. HTML would silently yield zero
    rules -- and references quoting HTML could never match a markdown
    ``source_doc`` -- so it is worth detecting and complaining about.
    """
    lowered = text.lower()
    return any(marker in lowered for marker in _HTML_MARKERS)


def extract_policy_rules(policy_document: str) -> List[PolicyRule]:
    """Split markdown into atomic bullet-level rules, each a verbatim slice.

    A bullet absorbs the indented, non-bullet lines that follow it, up to a
    blank line, the next bullet, or a heading -- so a rule whose substance
    continues on the next line is not truncated. Because the returned text is a
    slice of ``policy_document`` taken by offset, the document's own line breaks
    and indentation are preserved and the text stays an exact substring.

    Headings, blank lines and other prose are dropped.

    Raises:
        HtmlPolicyDocumentError: the document looks like rendered HTML and
            yielded no rules. A markdown document that merely mentions a tag
            still yields its rules and is accepted.
    """
    lines = policy_document.splitlines(keepends=True)
    starts: List[int] = []
    offset = 0
    for line in lines:
        starts.append(offset)
        offset += len(line)

    rules: List[PolicyRule] = []
    index = 0
    while index < len(lines):
        match = _BULLET.match(lines[index].rstrip("\n"))
        if match is None:
            index += 1
            continue

        indent, _marker, gap, content = match.groups()
        begin = starts[index] + len(indent) + 1 + len(gap)
        end = begin + len(content.rstrip())

        index += 1
        while index < len(lines):
            stripped = lines[index].strip()
            if not stripped:
                break
            if _BULLET.match(lines[index].rstrip("\n")) or stripped.startswith("#"):
                break
            if not lines[index][:1].isspace():
                break
            end = starts[index] + len(lines[index].rstrip())
            index += 1

        text = policy_document[begin:end]
        rules.append(PolicyRule(text=text, slug=slugify(text)[:60]))

    if not rules and looks_like_html(policy_document):
        raise HtmlPolicyDocumentError(
            "The policy document looks like rendered HTML and yielded no rules. "
            "Pass the markdown source instead: rules are found by their '- ' "
            "bullet markers, and every reference must be quotable verbatim from "
            "the markdown that source_doc names."
        )

    return rules


def load_system_vars(
    sys_var: Optional[Union[str, Path, Mapping[str, Any]]],
) -> SystemVars:
    """Normalize ``sys_var`` -- a mapping, a path to JSON, or nothing -- to :class:`SystemVars`.

    ``names`` keeps the input's own key order, minus :data:`NON_SUBJECT_KEYS`.
    """
    if sys_var is None:
        return SystemVars()
    if isinstance(sys_var, (str, Path)):
        raw = json.loads(Path(sys_var).read_text(encoding="utf-8"))
    else:
        raw = dict(sys_var)
    names = [key for key in raw if key not in NON_SUBJECT_KEYS]
    return SystemVars(names=names, raw=raw)
