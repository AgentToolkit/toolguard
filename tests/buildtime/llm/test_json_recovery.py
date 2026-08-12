"""Recovery from the one JSON defect models actually make: bare inner quotes.

A policy document that quotes a literal — ``obtain the user's explicit
confirmation ("yes")`` — makes models escape the quotes in one field and leave
them bare in another, in the same reply. The payload is complete and
brace-balanced; only the parse fails. These tests pin the two layers that get
the content back: a retry that tells the model what broke, and a last-resort
salvage for a model that will not cooperate.
"""

import json
from typing import Dict, List

import pytest

from toolguard.buildtime.llm.llm_base import LanguageModelBase

# Escaped inside "references", bare inside "description" -- the reported shape.
BARE_QUOTES_PAYLOAD = """```json
{
  "tool_name": "delete_record",
  "policy_items": [
    {
      "description": "The agent must first list the details of the action and obtain the user's explicit confirmation ("yes") before proceeding.",
      "references": ["obtain the user's explicit confirmation (\\"yes\\")"]
    }
  ]
}
```"""

# A payload whose bare quote is followed by a comma, which the salvage cannot
# tell from a delimiter -- used to exercise the retry path rather than salvage.
BARE_QUOTES_PAYLOAD_UNSALVAGEABLE = """```json
{"note": "he said "hello", then left", "n": 3}
```"""

GOOD_PAYLOAD = """```json
{"tool_name": "delete_record", "policy_items": []}
```"""


class ScriptedModel(LanguageModelBase):
    """Returns queued replies and records the messages it was asked with."""

    def __init__(self, replies: List[str]):
        self.replies = list(replies)
        self.seen: List[List[Dict]] = []

    async def generate(self, messages: List[Dict]) -> str:
        self.seen.append([dict(m) for m in messages])
        return self.replies.pop(0) if self.replies else "not json at all"


class AlwaysBareQuotes(LanguageModelBase):
    """Reproduces the defect however it is corrected, rewording each time."""

    def __init__(self):
        self.call_count = 0

    async def generate(self, messages: List[Dict]) -> str:
        self.call_count += 1
        return BARE_QUOTES_PAYLOAD.replace(
            "delete_record", f"delete_record_{self.call_count}"
        )


# --- the salvage ---------------------------------------------------------


def test_salvage_recovers_a_payload_with_bare_inner_quotes():
    model = ScriptedModel([])

    result = model.extract_json_from_string(BARE_QUOTES_PAYLOAD)

    assert result is not None
    item = result["policy_items"][0]
    assert item["description"].endswith('("yes") before proceeding.')
    assert item["references"] == ['obtain the user\'s explicit confirmation ("yes")']


@pytest.mark.parametrize(
    "payload",
    [
        '{"a": "b", "c": [1, 2], "d": {"e": "f"}}',
        '{"s": "comma, inside", "t": "colon: inside", "u": "brace } inside"}',
        '{"esc": "already \\"escaped\\" fine"}',
        '{"empty": "", "next": "v"}',
        '{"bracket": "an [array] inside", "n": null}',
    ],
)
def test_salvage_leaves_valid_payloads_untouched(payload):
    model = ScriptedModel([])

    assert model.extract_json_from_string(payload) == json.loads(payload)


def test_the_first_fenced_block_wins():
    """A model that shows an example before its answer must not fuse the two."""
    model = ScriptedModel([])

    text = (
        'For example:\n```json\n{"shape": "example"}\n```\n'
        'And here is the answer:\n```json\n{"shape": "answer"}\n```'
    )

    assert model.extract_json_from_string(text) == {"shape": "example"}


def test_an_unfenced_object_stops_at_its_own_closing_brace():
    model = ScriptedModel([])

    text = 'Here you go: {"a": {"b": "}"}} -- hope that helps!'

    assert model.extract_json_from_string(text) == {"a": {"b": "}"}}


@pytest.mark.parametrize(
    "payload",
    [
        "This is not JSON",
        '{"key": "value"',  # truncated
        "",
    ],
)
def test_salvage_does_not_invent_a_result(payload):
    model = ScriptedModel([])

    assert model.extract_json_from_string(payload) is None


# --- the repair turn ----------------------------------------------------


async def test_retry_tells_the_model_what_broke():
    model = ScriptedModel([BARE_QUOTES_PAYLOAD_UNSALVAGEABLE, GOOD_PAYLOAD])

    result = await model.chat_json([{"role": "user", "content": "generate a spec"}])

    assert result == {"tool_name": "delete_record", "policy_items": []}

    # The second attempt must carry the failed reply plus the parser's complaint,
    # otherwise the model has nothing new to work with and repeats itself.
    second_attempt = model.seen[1]
    assert len(second_attempt) > 1
    assert any(
        m["role"] == "assistant" and BARE_QUOTES_PAYLOAD_UNSALVAGEABLE in m["content"]
        for m in second_attempt
    )
    feedback = second_attempt[-1]
    assert feedback["role"] == "user"
    assert "JSON" in feedback["content"]


async def test_retry_does_not_resend_an_unchanged_prompt():
    model = ScriptedModel([])  # every reply is unparseable

    with pytest.raises(RuntimeError):
        await model.chat_json(
            [{"role": "user", "content": "generate a spec"}], max_retries=3
        )

    prompts = [json.dumps(msgs) for msgs in model.seen]
    assert len(prompts) == len(set(prompts)), "identical prompts were re-sent"


async def test_unrecoverable_response_still_raises_after_retries():
    model = ScriptedModel([])

    with pytest.raises(RuntimeError, match="valid JSON"):
        await model.chat_json([{"role": "user", "content": "hi"}], max_retries=2)


async def test_salvage_catches_a_model_that_will_not_fix_itself():
    """Salvage is a guess, so the model gets its own chances first."""
    model = AlwaysBareQuotes()

    result = await model.chat_json([{"role": "user", "content": "hi"}], max_retries=3)

    assert result["policy_items"][0]["description"].endswith(
        '("yes") before proceeding.'
    )
    assert model.call_count == 3, "salvage must not pre-empt the repair turns"
