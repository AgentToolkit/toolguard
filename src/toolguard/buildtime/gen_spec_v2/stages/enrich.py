"""The ``enrich`` stage: when a rule applies, what it needs, and what's missing.

This is where a v2 spec earns its shape. Each item gets several votes on one
question — how would you actually enforce this? — reconciled by a pure
function, then filtered against reality: a system variable nobody declared or
a tool that does not exist is dropped rather than written into the spec.

An item whose gap cannot be closed is **kept**, carrying its
``pending_for_user`` alert. Surfacing the gap is the point of the field; the
adapter is what stops such an item reaching codegen.
"""

import asyncio
from typing import List

from loguru import logger

from toolguard.buildtime.gen_spec.data_types import ToolInfo
from toolguard.buildtime.gen_spec_v2 import prompts
from toolguard.buildtime.gen_spec_v2.context import GenContext
from toolguard.buildtime.gen_spec_v2.models import PolicyItemV2, Requires
from toolguard.buildtime.gen_spec_v2.reconcile import Reconciled, reconcile
from toolguard.buildtime.gen_spec_v2.stages._shared import item_summary, messages
from toolguard.buildtime.gen_spec_v2.sysvars import keep_declared
from toolguard.buildtime.llm import I_TG_LLM


def _validated_requires(
    reconciled: Reconciled, ctx: GenContext, item_id: str
) -> Requires:
    """Drop anything the runtime could not actually supply.

    An undeclared system variable or an unknown tool name would compile into a
    guard reading something that does not exist, so neither is trusted just
    because the model named it.
    """
    known_tools = set(ctx.tool_names())
    history = reconciled.requires.tool_history or []
    usable = []
    for entry in history:
        if entry.tool in known_tools:
            usable.append(entry)
        else:
            logger.warning(
                "{}: dropping tool_history entry for unknown tool '{}'",
                item_id,
                entry.tool,
            )

    return Requires(
        system_vars=keep_declared(
            reconciled.requires.system_vars, ctx.system_vars, context=item_id
        ),
        tool_history=usable or None,
        message_history=reconciled.requires.message_history,
    )


def _validated_references(reconciled: Reconciled, item: PolicyItemV2) -> List[str]:
    """Keep or drop the item's references — never add.

    The votes only validate; intersecting with what the item arrived with means
    a stray vote cannot introduce a reference that was never in the document.
    Validation that removes everything falls back to the original set: an item
    with no evidence at all is worse than one with imperfect evidence.
    """
    original = list(item.references)
    validated = [r for r in reconciled.references if r in original]
    return validated or original


async def _enrich_item(
    llm: I_TG_LLM, ctx: GenContext, tool: ToolInfo, item: PolicyItemV2, votes: int
) -> Reconciled:
    system = prompts.system("enrich")
    user = prompts.enrich_user(ctx, tool, item_summary(item))
    results = await asyncio.gather(
        *[llm.chat_json(messages(system, user)) for _ in range(votes)]
    )
    return reconcile(list(results))


async def run_enrich(
    llm: I_TG_LLM,
    ctx: GenContext,
    tool: ToolInfo,
    items: List[PolicyItemV2],
    votes: int,
) -> List[PolicyItemV2]:
    """Enrich every item in place and return them all, in order."""
    if not items:
        return []

    results = await asyncio.gather(
        *[_enrich_item(llm, ctx, tool, item, votes) for item in items]
    )

    for item, reconciled in zip(items, results):
        item.trigger = reconciled.trigger
        item.requires = _validated_requires(reconciled, ctx, item.id)
        item.references = _validated_references(reconciled, item)
        item.pending_for_user = reconciled.pending_for_user

        if item.pending_for_user:
            logger.info(
                "{}: needs a human — {}",
                item.id,
                "; ".join(p.question for p in item.pending_for_user),
            )

    return items
