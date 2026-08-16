"""The create stage: one call binding the policy document's rules to one tool."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Set, Tuple

from toolguard.buildtime.gen_spec.data_types import ToolInfo
from toolguard.buildtime.gen_spec_v2.context import GenContext
from toolguard.buildtime.gen_spec_v2.data_types import (
    PolicyItemV2,
    Requires,
    slugify,
    unique_id,
)
from toolguard.buildtime.gen_spec_v2.prompts import create as create_prompt
from toolguard.buildtime.gen_spec_v2.utils import ask_json
from toolguard.buildtime.llm import I_TG_LLM


class ToolMetadata:
    """What the model believes about the tool. Used in prompts, never written.

    The spec schema has no place for it -- tool metadata is not enforceable
    content -- but later stages read better with it in front of them.
    """

    def __init__(self, is_read_only: bool = False, user_enrichment: str = "") -> None:
        self.is_read_only = is_read_only
        self.user_enrichment = user_enrichment


def build_items(
    raw_items: Sequence[Any], tool_name: str, taken: Set[str]
) -> List[PolicyItemV2]:
    """Turn raw create/expand output into items, normalizing ids.

    An item without a reference is not grounded in the policy document, so it is
    not built at all -- ``references`` is ``minItems: 1`` and a rule nobody can
    trace back to the document is not a rule. ``taken`` is updated in place with
    every id handed out, so a second call keeps ids unique across both.
    """
    items: List[PolicyItemV2] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        name = raw.get("name")
        references = list(raw.get("references") or [])
        if not name or not references:
            continue

        raw_id = str(raw.get("id") or "")
        slug = raw_id.split(".", 1)[1] if "." in raw_id else name
        item_id = unique_id(tool_name, slugify(slug), taken)
        taken.add(item_id)

        items.append(
            PolicyItemV2(
                id=item_id,
                name=name,
                description=raw.get("description", ""),
                references=references,
                trigger="pre_tool",
                requires=Requires(),
            )
        )
    return items


async def run_create(
    llm: I_TG_LLM, ctx: GenContext, tool: ToolInfo
) -> Tuple[ToolMetadata, List[PolicyItemV2]]:
    """Bind the context's policy rules to ``tool`` with a single call."""
    response: Dict = await ask_json(
        llm, create_prompt.SYSTEM, create_prompt.user(ctx, tool)
    )

    raw_meta = response.get("tool_info")
    metadata = (
        ToolMetadata(
            is_read_only=bool(raw_meta.get("is_read_only", False)),
            user_enrichment=str(raw_meta.get("user_enrichment", "")),
        )
        if isinstance(raw_meta, dict)
        else ToolMetadata()
    )

    items = build_items(response.get("policy_items") or [], tool.name, set())
    return metadata, items
