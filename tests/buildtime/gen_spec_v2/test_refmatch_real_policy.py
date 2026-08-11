"""Grounding against the real employee policy document.

Every reference in the ground-truth specs was quoted from
``tests/data/specs_v2_inputs/guidance.txt``, so grounding each one must
return that same span. This is the regression gate on the matcher: a
normalization or segmentation change that starts mangling real references
fails here, where the synthetic tests would not notice.
"""

from pathlib import Path

import pytest

from toolguard.buildtime.gen_spec_v2.refmatch import ground
from toolguard.buildtime.gen_spec_v2.serialize import load_spec

from .conftest import requires_corpus

GUIDANCE = Path("tests/data/specs_v2_inputs/guidance.txt")
SPEC_DIR = Path("tests/data/specs_v2")

pytestmark = requires_corpus


def _references():
    doc = GUIDANCE.read_text(encoding="utf-8")
    for path in sorted(SPEC_DIR.glob("*.json")):
        for item in load_spec(path).policy_items:
            for reference in item.references:
                yield doc, item.id, reference


# Guarded: this module reads the corpus at import time, and an unguarded read
# aborts collection for the whole suite when tests/data/ is absent.
ALL_REFERENCES = list(_references()) if GUIDANCE.is_file() else []


def test_the_corpus_is_not_empty():
    assert len(ALL_REFERENCES) == 95


@pytest.mark.parametrize(
    "doc,item_id,reference",
    ALL_REFERENCES,
    ids=[f"{item_id}#{i}" for i, (_, item_id, _) in enumerate(ALL_REFERENCES)],
)
def test_real_reference_grounds_to_itself(doc, item_id, reference):
    assert ground(reference, doc) == [reference]
