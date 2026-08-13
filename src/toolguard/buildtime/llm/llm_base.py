import json
import re
from abc import ABC
from typing import Dict, List, Optional, Tuple

from loguru import logger

from .i_tg_llm import I_TG_LLM

# Non-greedy: a reply that shows an example block before its real answer must
# yield the first block, not a fusion of the two.
_FENCED = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)

_REPAIR_INSTRUCTION = (
    "Your previous reply could not be parsed as JSON. The parser reported:\n"
    "{error}\n\n"
    "Return the same content as a single valid JSON object and nothing else. "
    'Every double quote inside a string value must be escaped as \\" -- this '
    "applies to every field, not just some of them. Do not drop or summarize "
    "any content, and do not add commentary before or after the object."
)

# A `"` inside a string ends it only if the next non-space character is one of
# these (or the text runs out). Anything else means the quote was content.
_STRING_ENDERS = frozenset(",}]:")


class LanguageModelBase(I_TG_LLM, ABC):
    async def chat_json(self, messages: List[Dict], max_retries: int = 5) -> Dict:
        """Ask for JSON, and on a parse failure tell the model what broke.

        The retry is a repair turn, not a replay: the unparseable reply and the
        parser's own complaint go back to the model. Re-sending the original
        prompt unchanged is what made a single quoted literal in a policy
        document cost every attempt -- the model has no new information, so it
        reproduces the same mistake five times.
        """
        attempt_messages = list(messages)
        previous_response: Optional[str] = None
        last_response = ""
        attempts_made = 0

        for attempt in range(1, max_retries + 1):
            last_response = await self.generate(attempt_messages)
            attempts_made = attempt
            # Salvage is a guess, so spend the model's own attempts first.
            parsed, error = self.parse_json_response(last_response, allow_salvage=False)
            if parsed is not None:
                return parsed

            if last_response == previous_response:
                # The model has ignored the same correction twice. Further
                # attempts cost tokens and buy nothing.
                logger.warning(
                    "Model repeated an identical unparseable reply; abandoning "
                    "after {} attempt(s)",
                    attempt,
                )
                break

            logger.warning(
                "Response was not valid JSON ({}). Asking the model to fix it "
                "(attempt {}/{})",
                error,
                attempt,
                max_retries,
            )
            attempt_messages = [
                *messages,
                {"role": "assistant", "content": last_response},
                {
                    "role": "user",
                    "content": _REPAIR_INSTRUCTION.format(error=error or "unknown"),
                },
            ]
            previous_response = last_response

        # Out of model attempts. Guess, loudly, rather than lose the content.
        parsed, error = self.parse_json_response(last_response, allow_salvage=True)
        if parsed is not None:
            return parsed

        raise RuntimeError(
            f"Could not obtain valid JSON from the model after {attempts_made} "
            f"attempt(s): {error}"
        )

    def parse_json_response(
        self, s: str, allow_salvage: bool = True
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """Parse a model reply, returning ``(object, error)``.

        Exactly one side is populated. The error text is the parser's own
        message, so it can be handed back to the model as feedback.

        With ``allow_salvage``, a structurally complete reply whose only defect
        is a bare double quote inside a string value is repaired locally.
        """
        candidate = _json_candidate(s)
        if candidate is None:
            return None, "no JSON object found in the response"

        try:
            return json.loads(candidate), None
        except json.JSONDecodeError as exc:
            strict_error = str(exc)

        if not allow_salvage:
            return None, strict_error

        # Last resort. The model produced something structurally complete but
        # left a double quote bare inside a string value -- the defect that
        # shows up whenever a policy document quotes a literal. Escaping those
        # quotes is a guess: a bare quote followed by a comma is
        # indistinguishable from a delimiter, and guessing wrong can silently
        # shorten a string value. Hence last, and hence loud.
        repaired, repairs = _escape_bare_quotes(candidate)
        if repairs:
            try:
                parsed = json.loads(repaired)
            except json.JSONDecodeError:
                pass
            else:
                logger.warning(
                    "Salvaged an unparseable response by escaping {} bare quote(s) "
                    "inside string values. The affected values may be truncated "
                    "-- review them.",
                    repairs,
                )
                return parsed, None

        return None, strict_error

    def extract_json_from_string(self, s: str) -> Optional[Dict]:
        """The object, or ``None`` if nothing could be recovered."""
        parsed, _ = self.parse_json_response(s)
        return parsed


def _json_candidate(s: str) -> Optional[str]:
    """Return the substring most likely to be the JSON object.

    Prefers a fenced block, then falls back to the outermost brace-balanced
    span. The balance scan is string-aware so a brace inside a string value
    does not end the object early.
    """
    if not s:
        return None

    match = _FENCED.search(s)
    if match:
        return match.group(1).strip()

    start = s.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    i = start
    while i < len(s):
        ch = s[i]
        if in_string:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
        i += 1

    # Unbalanced -- hand back everything from the first brace so the parser
    # produces a real error message for the repair turn.
    return s[start:]


def _escape_bare_quotes(s: str) -> Tuple[str, int]:
    """Escape double quotes that appear inside a JSON string value.

    Returns the rewritten text and the number of quotes escaped. Heuristic by
    nature -- see the caller for why it is a last resort.
    """
    out: List[str] = []
    i = 0
    n = len(s)
    in_string = False
    repairs = 0

    while i < n:
        ch = s[i]
        if not in_string:
            out.append(ch)
            if ch == '"':
                in_string = True
            i += 1
            continue

        if ch == "\\":
            out.append(s[i : i + 2])
            i += 2
            continue

        if ch == '"':
            j = i + 1
            while j < n and s[j] in " \t\r\n":
                j += 1
            if j >= n or s[j] in _STRING_ENDERS:
                out.append(ch)
                in_string = False
            else:
                out.append('\\"')
                repairs += 1
            i += 1
            continue

        out.append(ch)
        i += 1

    return "".join(out), repairs
