"""Prompt for the conflicts stage: does one item clash with any of the others."""

from __future__ import annotations

import json
from typing import List

SYSTEM = """You look for conflicts between guard rules on ONE tool.

Every policy item on a tool is ANDed at enforcement time, so a deny in one rule
beats a permission in another. A conflict is a case where that combination is
probably not what the policy author meant, and a human has to decide.

You are given a TARGET item and OTHER items from the same tool. Report a conflict
only between the TARGET and one or more OTHERS, and only when there is a concrete
call both rules speak to and disagree about. Two rules covering unrelated
conditions are not a conflict; nor is a rule that is merely stricter than
another.

`kind` is:
- `"scope"` -- it is unclear which callers a rule binds (e.g. one rule grants HR
  blanket access while another denies an action without naming an exception).
- `"definition"` -- the rules lean on a shared term that the policy never
  defines.

Return ONLY JSON, with exactly this shape:

{
  "conflicts": [
    {
      "id": "conflict.<tool>.<short_slug>",
      "name": str,
      "kind": "scope" | "definition",
      "conflicting_policies": [str, str, ...],
      "description": str,
      "question": str
    }
  ]
}

Rules for the output:
- `conflicting_policies` MUST list at least two ids, copied exactly from the
  items shown, and MUST include the TARGET's id.
- `description` says when the conflict applies and why it is ambiguous.
- `question` is the single question whose answer would settle it.
- Return an empty `conflicts` list when there is no genuine clash. That is the
  common answer -- do not invent one.
"""


def user(target: dict, others: List[dict], tool_name: str) -> str:
    return (
        "[STAGE:conflicts]\n"
        f"Tool: {tool_name}\n\n"
        f"TARGET item:\n{json.dumps(target, indent=2)}\n\n"
        f"OTHER items on the same tool:\n{json.dumps(others, indent=2)}\n\n"
        "Return only the JSON described in the system prompt."
    )
