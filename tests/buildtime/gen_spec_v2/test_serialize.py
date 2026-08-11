"""Byte parity of the v2 serializer against smith's ground-truth specs.

These fixtures were produced by smith's generator and are the definition of
the on-disk format: key order and omit-when-empty behavior included. A
load -> dump round trip must reproduce them exactly, so a future change to
the models cannot quietly reorder or drop a key.
"""

from pathlib import Path

import pytest

from toolguard.buildtime.gen_spec_v2.serialize import dump_spec_str, load_spec

from .conftest import CORPUS_SPECS_DIR

FIXTURE_DIR = CORPUS_SPECS_DIR
FIXTURES = sorted(FIXTURE_DIR.glob("*.json"))


def _expected(path: Path) -> str:
    """The fixture's text with the one deliberate normalization applied.

    Smith's enrich prompt asks for `missing_var`, but two fixtures contain
    `missing_variable` (LLM drift that smith's archive check never matched).
    v2 normalizes the alias, so those two files legitimately round-trip to
    the canonical spelling.
    """
    return path.read_text(encoding="utf-8").replace(
        '"type": "missing_variable"', '"type": "missing_var"'
    )


def test_fixtures_are_present():
    # Guards against a glob that silently matches nothing, which would turn the
    # parity gate below into a test that passes by running zero cases.
    assert len(FIXTURES) == 6


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_fixture_round_trips_byte_identical(path: Path):
    assert dump_spec_str(load_spec(path)) == _expected(path)


def test_pending_type_alias_is_normalized():
    spec = load_spec(FIXTURE_DIR / "set_passport.json")
    pending = [p for item in spec.policy_items for p in item.pending_for_user]
    types = {p.type.value for p in pending}
    assert "missing_var" in types
    assert "missing_variable" not in types
