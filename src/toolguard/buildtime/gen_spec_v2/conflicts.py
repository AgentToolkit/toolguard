"""Finding policy items that disagree, and recording the question that settles it.

All of a tool's policy items must hold together, so a permission granted by one
and a prohibition written by another silently resolve to "denied". That is
often not what the policy author intended, and it is invisible in the items
themselves — hence a separate pass that reports the pair and the question a
human needs to answer.

Detection is pairwise *within* a tool (item ``i`` against items ``i+1..n``),
which keeps every prompt bounded by one tool's item count instead of the whole
spec set. A conflict may still name items from other tools, and
:func:`attach_conflicts` routes those to every tool involved: with no
``global.json`` in v2, each spec has to carry its own conflicts to stay
self-contained.
"""

import asyncio
from typing import Any, Dict, Iterable, List, Sequence

from loguru import logger

from toolguard.buildtime.gen_spec_v2 import prompts
from toolguard.buildtime.gen_spec_v2.models import Conflict, SpecV2
from toolguard.buildtime.gen_spec_v2.stages._shared import dict_list, messages
from toolguard.buildtime.llm import I_TG_LLM


def _as_dict(item) -> Dict[str, Any]:
    return {"id": item.id, "name": item.name, "description": item.description}


async def _tool_conflicts(llm: I_TG_LLM, spec: SpecV2) -> List[Dict[str, Any]]:
    items = [_as_dict(item) for item in spec.policy_items]
    if len(items) < 2:
        return []

    system = prompts.system("conflicts")
    calls = [
        llm.chat_json(
            messages(
                system,
                prompts.conflicts_user(spec.tool_name, items[i], items[i + 1 :]),
            )
        )
        for i in range(len(items) - 1)
    ]

    responses = await asyncio.gather(*calls)
    raw: List[Dict[str, Any]] = []
    for response in responses:
        raw.extend(dict_list(response, "conflicts"))
    return raw


async def find_conflicts(llm: I_TG_LLM, specs: Sequence[SpecV2]) -> List[Conflict]:
    """Detect conflicts across ``specs``, deduped by id, first-seen winning.

    A malformed entry is skipped rather than raised: one bad sub-response must
    not cost the run every other conflict it found. A conflict naming no known
    policy item is also dropped — there is nothing a human could act on.
    """
    known_items = {item.id for spec in specs for item in spec.policy_items}

    results = await asyncio.gather(*[_tool_conflicts(llm, spec) for spec in specs])

    conflicts: List[Conflict] = []
    seen = set()
    for raw_conflicts in results:
        for raw in raw_conflicts:
            try:
                conflict = Conflict.model_validate({**raw, "resolution": None})
            except Exception:  # noqa: BLE001 - one bad entry must not lose the rest
                logger.warning("Skipping malformed conflict entry: {}", raw)
                continue

            if conflict.id in seen:
                continue
            if not any(p in known_items for p in conflict.conflicting_policies):
                logger.warning(
                    "Dropping conflict '{}': names no known policy item", conflict.id
                )
                continue

            seen.add(conflict.id)
            conflicts.append(conflict)

    return conflicts


def _tools_of(conflict: Conflict) -> Iterable[str]:
    return {
        policy_id.split(".", 1)[0]
        for policy_id in conflict.conflicting_policies
        if "." in policy_id
    }


def attach_conflicts(specs: Sequence[SpecV2], conflicts: Sequence[Conflict]) -> None:
    """Replace each spec's ``conflicts`` with the ones that involve it, in place.

    Replacing rather than appending makes a rerun idempotent. A conflict
    spanning several tools is attached to each of them, so no signal is lost
    now that there is no shared spec to hold it.
    """
    by_tool = {spec.tool_name: spec for spec in specs}
    for spec in specs:
        spec.conflicts = []

    for conflict in conflicts:
        involved = [tool for tool in _tools_of(conflict) if tool in by_tool]
        if not involved:
            logger.warning(
                "Dropping conflict '{}': none of its tools are in this spec set",
                conflict.id,
            )
            continue
        for tool in sorted(involved):
            by_tool[tool].conflicts.append(conflict)
