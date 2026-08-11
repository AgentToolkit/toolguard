"""The acting user's variables: loading, rendering, and validation.

A policy like "HR may edit all employees' data" is only enforceable if the
runtime supplies the acting user's department. ``system_vars`` is how the
caller declares which such variables exist, so generation can reference them
by name instead of inventing them.

Values may be any shape. A list is read as the closed set of allowed values, a
scalar as one example of the shape to expect, and a nested mapping or list is
kept and rendered as-is — a structured attribute of the acting user is still an
attribute of the acting user.

Two keys are excluded: ``action_list`` and ``action_description``, which
describe the agent's own tools rather than the acting user, and appear in real
``system_vars.json`` files alongside the subject variables.
"""

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

from loguru import logger
from pydantic import BaseModel, Field

SUBJECT_PATH = "input.extensions.subject"

NON_SUBJECT_KEYS = frozenset({"action_list", "action_description"})
"""Keys that describe the agent's tools, not the acting user."""

SystemVarsInput = Union[Dict[str, Any], str, Path, None]


class SystemVars(BaseModel):
    """The declared subject variables and their values."""

    raw: Dict[str, Any] = Field(default_factory=dict)

    @property
    def names(self) -> List[str]:
        return list(self.raw)


def load_system_vars(source: SystemVarsInput) -> SystemVars:
    """Load system variables from a dict, a path to ``sys_var.json``, or nothing.

    Values of any shape are kept, including nested ones. Only
    :data:`NON_SUBJECT_KEYS` are dropped. Raises ``ValueError`` when a file does
    not hold a JSON object, since a list or scalar has no variable names to
    offer.
    """
    if source is None:
        return SystemVars()

    if isinstance(source, dict):
        data: Dict[str, Any] = dict(source)
        origin = "system_vars"
    else:
        path = Path(source)
        data = json.loads(path.read_text(encoding="utf-8"))
        origin = str(path)
        if not isinstance(data, dict):
            raise ValueError(
                f"{path}: expected a JSON object of system variables, "
                f"got {type(data).__name__}"
            )

    kept = {}
    for name, value in data.items():
        if name in NON_SUBJECT_KEYS:
            logger.debug(
                "{}: ignoring '{}' — describes tools, not the user", origin, name
            )
            continue
        kept[name] = value
    return SystemVars(raw=kept)


def render_system_vars(system_vars: SystemVars) -> str:
    """Render each variable's name, access path, and domain, one per line.

    A list value is a closed set of allowed values; anything else is one example
    of the shape to expect, nested structures included. The access path is
    included so the LLM can tell subject variables from tool parameters.
    """
    if not system_vars.raw:
        return "(no system variables available)"

    lines = []
    for name, value in system_vars.raw.items():
        path = f"{SUBJECT_PATH}.{name}"
        kind = "allowed values" if isinstance(value, list) else "example value"
        lines.append(f"- {name} ({path}): {kind} = {json.dumps(value)}")
    return "\n".join(lines)


def keep_declared(
    names: Iterable[str], system_vars: SystemVars, context: Optional[str] = None
) -> List[str]:
    """Keep only names that are actually declared, deduped, in first-seen order.

    A generated spec that references a variable nobody supplies would compile
    into a guard reading an absent value, so an undeclared name is dropped and
    logged rather than trusted.
    """
    declared = system_vars.raw
    kept: List[str] = []
    for name in names:
        if name in kept:
            continue
        if name not in declared:
            logger.warning(
                "Dropping undeclared system variable '{}'{}",
                name,
                f" in {context}" if context else "",
            )
            continue
        kept.append(name)
    return kept
