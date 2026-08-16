"""Finding conflicts between a tool's policy items, and routing them.

Detection is per tool and pairwise: for a tool's ``n`` items, call ``i`` compares
item ``i`` against items ``i+1..n-1``. That bounds every prompt by one tool's
item count, which is what keeps a response from being truncated mid-JSON on a
tool with many rules. The cost is that a model may cite a neighbouring tool's
items anyway, so :func:`split_and_attach` is what makes each conflict satisfy the
schema: every id resolves inside the file that carries it, and at least two do.

A question that genuinely spans several tools is not dropped -- it is recorded
once per affected tool under a shared id slug, which is how the reference corpus
carries its cross-tool definition question.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Sequence

from loguru import logger

from toolguard.buildtime.gen_spec_v2.data_types import (
    Conflict,
    PolicyItemV2,
    ToolGuardSpecV2,
    slugify,
)
from toolguard.buildtime.gen_spec_v2.prompts import conflicts as conflicts_prompt
from toolguard.buildtime.gen_spec_v2.utils import ask_json
from toolguard.buildtime.llm import I_TG_LLM

CONFLICT_KINDS = ("scope", "definition")

#: A tool needs at least this many of its own items in a conflict to carry it.
MIN_POLICIES = 2


def _tool_of(policy_id: str) -> str:
    return policy_id.split(".", 1)[0]


def split_and_attach(
    specs: Dict[str, ToolGuardSpecV2], raw_conflicts: Sequence[Any]
) -> None:
    """Attach each raw conflict to every spec that can carry it, in place.

    Ids naming no known item are discarded first. The rest are grouped by tool,
    and every tool contributing at least :data:`MIN_POLICIES` of its own items
    gets a copy whose id is ``conflict.<tool>.<slug>`` and whose
    ``conflicting_policies`` are only that tool's items. A conflict no tool
    qualifies for is dropped with a warning; so is a malformed one, without
    costing the others.

    Duplicate ids are collapsed, but only once a conflict has actually been
    attached -- so a malformed copy sharing an id does not shadow a good one.
    """
    ids_by_tool = {
        tool: {item.id for item in spec.policy_items} for tool, spec in specs.items()
    }
    known_ids = {item_id for ids in ids_by_tool.values() for item_id in ids}
    attached_ids: set = set()

    for raw in raw_conflicts:
        if not isinstance(raw, dict):
            continue
        try:
            raw_id = raw["id"]
            name = raw["name"]
            kind = raw["kind"]
            policies = list(raw["conflicting_policies"])
            description = raw["description"]
            question = raw["question"]
        except (KeyError, TypeError):
            logger.warning(f"Skipping malformed conflict: {raw!r}")
            continue

        if raw_id in attached_ids:
            continue
        if kind not in CONFLICT_KINDS:
            logger.warning(f"Skipping conflict {raw_id!r} of unknown kind {kind!r}")
            continue

        grouped: Dict[str, List[str]] = {}
        for policy_id in policies:
            if policy_id not in known_ids:
                continue
            grouped.setdefault(_tool_of(policy_id), []).append(policy_id)

        slug = slugify(str(raw_id).rsplit(".", 1)[-1])
        attached = False
        for tool, tool_policies in grouped.items():
            if tool not in specs or len(tool_policies) < MIN_POLICIES:
                continue
            specs[tool].conflicts.append(
                Conflict(
                    id=f"conflict.{tool}.{slug}",
                    name=name,
                    kind=kind,
                    conflicting_policies=tool_policies,
                    description=description,
                    question=question,
                )
            )
            attached = True

        if attached:
            attached_ids.add(raw_id)
        else:
            logger.warning(
                f"Dropping conflict {raw_id!r}: no tool contributes "
                f"{MIN_POLICIES} of its own policy items"
            )


def _as_payload(item: PolicyItemV2) -> Dict[str, str]:
    return {"id": item.id, "name": item.name, "description": item.description}


async def _tool_conflicts(
    llm: I_TG_LLM, tool_name: str, payloads: Sequence[Dict[str, str]]
) -> List[dict]:
    """Upper-triangle pairwise calls for one tool: item i against items after it."""
    responses = await asyncio.gather(
        *[
            ask_json(
                llm,
                conflicts_prompt.SYSTEM,
                conflicts_prompt.user(payloads[i], list(payloads[i + 1 :]), tool_name),
            )
            for i in range(len(payloads) - 1)
        ]
    )

    raw: List[dict] = []
    for response in responses:
        if not isinstance(response, dict):
            continue
        for entry in response.get("conflicts") or []:
            raw.append(entry)
    return raw


async def find_conflicts(
    llm: I_TG_LLM, specs: Dict[str, ToolGuardSpecV2]
) -> List[dict]:
    """Look for conflicts within each tool that has at least two policy items.

    A tool with fewer than two items has no pair to compare, so it costs no call
    at all. Every tool's calls run concurrently; the raw responses are returned
    unvalidated for :func:`split_and_attach` to route and filter.
    """
    candidates = {
        tool: [_as_payload(item) for item in spec.policy_items]
        for tool, spec in specs.items()
        if len(spec.policy_items) >= MIN_POLICIES
    }
    if not candidates:
        return []

    results = await asyncio.gather(
        *[_tool_conflicts(llm, tool, payloads) for tool, payloads in candidates.items()]
    )
    return [entry for result in results for entry in result]
