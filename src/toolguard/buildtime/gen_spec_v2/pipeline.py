"""Orchestration and the public v2 entry points.

Three calls, because the caller — not toolguard — knows when a complete spec
set exists:

- :func:`generate_guard_specs_v2` writes one spec per tool and nothing else.
- :func:`generate_spec_conflicts_v2` reads a complete set and records the
  conflicts within it.
- :func:`generate_guard_specs_v2_full` does both, for a plain full build.

Splitting them keeps partial regeneration safe: regenerating one tool touches
only that tool's file, and the conflicts pass rebuilds conflicts from whatever
is on disk.
"""

import asyncio
from pathlib import Path
from typing import List, Optional, Sequence

from loguru import logger
from pydantic import BaseModel, Field

from toolguard.buildtime.compat.strenum import StrEnum
from toolguard.buildtime.gen_spec.data_types import ToolInfo
from toolguard.buildtime.gen_spec_v2.conflicts import attach_conflicts, find_conflicts
from toolguard.buildtime.gen_spec_v2.context import GenContext
from toolguard.buildtime.gen_spec_v2.models import SpecDebugV2, SpecV2
from toolguard.buildtime.gen_spec_v2.refmatch import ground_spec
from toolguard.buildtime.gen_spec_v2.serialize import dump_spec, load_specs
from toolguard.buildtime.gen_spec_v2.stages import (
    run_create,
    run_enrich,
    run_examples,
    run_expand,
    run_review,
)
from toolguard.buildtime.gen_spec_v2.sysvars import SystemVarsInput
from toolguard.buildtime.gen_spec_v2.tools_input import TOOLS_V2
from toolguard.buildtime.llm import I_TG_LLM


class ToolErrorPolicy(StrEnum):
    """What to do when one tool's generation raises."""

    skip = "skip"
    """Record the failure and let every other tool finish."""

    raise_ = "raise"
    """Abort the whole run."""


class SpecV2Options(BaseModel):
    """Knobs for a v2 run. The defaults are what a normal build should use."""

    review_votes: int = Field(default=5, ge=1)
    enrich_votes: int = Field(default=3, ge=1)
    add_iterations: int = Field(default=3, ge=0)
    include_examples: bool = True
    example_number: Optional[int] = Field(
        default=None,
        description="None = let the model choose, >0 = exactly that many per side",
    )
    max_concurrency: int = Field(default=8, ge=1)
    on_tool_error: str = "skip"


async def _generate_one(
    llm: I_TG_LLM,
    ctx: GenContext,
    tool: ToolInfo,
    source_doc: str,
    options: SpecV2Options,
) -> SpecV2:
    """Run create -> expand -> review -> enrich -> examples for one tool."""
    tool_info, items = await run_create(llm, ctx, tool)
    items = await run_expand(llm, ctx, tool, items, options.add_iterations)
    items, archive = await run_review(llm, ctx, tool, items, options.review_votes)
    items = await run_enrich(llm, ctx, tool, items, options.enrich_votes)

    if options.include_examples and options.example_number != 0:
        await run_examples(llm, ctx, tool, items, options.example_number)

    spec = SpecV2(
        tool_name=tool.name,
        source_doc=source_doc,
        policy_items=items,
        debug=SpecDebugV2(tool_info=tool_info, archive=archive),
    )
    ground_spec(spec, ctx.policy_text)
    return spec


async def generate_guard_specs_v2(
    policy_text: str,
    tools: TOOLS_V2,
    llm: I_TG_LLM,
    work_dir: str | Path,
    *,
    tools2guard: Optional[Sequence[str]] = None,
    system_vars: SystemVarsInput = None,
    source_doc: str = "",
    options: Optional[SpecV2Options] = None,
) -> List[SpecV2]:
    """Generate one v2 spec per tool and write it to ``work_dir``.

    Every requested tool gets a file, including one with no applicable rules:
    an empty spec is the answer "no rule governs this tool", and its absence
    would be indistinguishable from a failed run.

    Writes ``<tool>.json``. Note these are the same filenames v1 uses, and v1's
    loader will accept them while silently ignoring the v2 fields — point v2 at
    its own directory rather than sharing one with v1 output.
    """
    options = options or SpecV2Options()
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    ctx = GenContext.build(policy_text, tools, system_vars)

    if tools2guard is None:
        targets = list(ctx.tools)
    else:
        known = set(ctx.tool_names())
        unknown = [name for name in tools2guard if name not in known]
        if unknown:
            raise ValueError(f"Unknown tool(s) in tools2guard: {', '.join(unknown)}")
        targets = [tool for tool in ctx.tools if tool.name in set(tools2guard)]

    semaphore = asyncio.Semaphore(options.max_concurrency)

    async def guarded(tool: ToolInfo):
        async with semaphore:
            try:
                return await _generate_one(llm, ctx, tool, source_doc, options)
            except Exception as ex:  # noqa: BLE001 - per-tool isolation by design
                if options.on_tool_error == "raise":
                    raise
                logger.error("Spec generation failed for '{}': {}", tool.name, ex)
                return None

    results = await asyncio.gather(*[guarded(tool) for tool in targets])

    specs = [spec for spec in results if spec is not None]
    for spec in specs:
        dump_spec(spec, work_dir / f"{spec.tool_name}.json")

    logger.debug("gen_spec_v2: wrote {}/{} spec(s)", len(specs), len(targets))
    return specs


async def generate_spec_conflicts_v2(
    llm: I_TG_LLM,
    work_dir: str | Path,
    *,
    specs: Optional[Sequence[SpecV2]] = None,
    rewrite: bool = True,
) -> List[SpecV2]:
    """Find conflicts across a complete spec set and record them on each spec.

    Reads ``work_dir`` when ``specs`` is not given, so a caller that generated
    tools in separate runs still gets conflicts computed over all of them. Every
    spec is rewritten with its conflicts replaced, which makes a rerun
    idempotent; ``rewrite=False`` computes without touching disk.
    """
    work_dir = Path(work_dir)
    spec_list = list(specs) if specs is not None else load_specs(work_dir)

    if not spec_list:
        logger.warning("No specs found in {}; nothing to check for conflicts", work_dir)
        return []

    conflicts = await find_conflicts(llm, spec_list)
    attach_conflicts(spec_list, conflicts)

    if rewrite:
        for spec in spec_list:
            if spec.conflicts or (work_dir / f"{spec.tool_name}.json").exists():
                dump_spec(spec, work_dir / f"{spec.tool_name}.json")

    logger.debug(
        "gen_spec_v2: {} conflict(s) across {} spec(s)", len(conflicts), len(spec_list)
    )
    return spec_list


async def generate_guard_examples_v2(
    policy_text: str,
    tools: TOOLS_V2,
    llm: I_TG_LLM,
    work_dir: str | Path,
    *,
    specs: Optional[Sequence[SpecV2]] = None,
    system_vars: SystemVarsInput = None,
    example_number: Optional[int] = None,
    rewrite: bool = True,
) -> List[SpecV2]:
    """Rerun only the examples stage for specs already generated.

    The counterpart to v1's ``generate_guard_examples``. Examples are what test
    generation works from, so rewording them should not cost a full spec run —
    everything else on each item is left exactly as it was.

    Reads ``work_dir`` when ``specs`` is not given. A spec whose tool is absent
    from ``tools`` is skipped rather than guessed at: without the tool's
    parameters there is nothing concrete to write an example about.
    """
    work_dir = Path(work_dir)
    spec_list = list(specs) if specs is not None else load_specs(work_dir)

    if not spec_list:
        logger.warning(
            "No specs found in {}; nothing to regenerate examples for", work_dir
        )
        return []

    ctx = GenContext.build(policy_text, tools, system_vars)
    known = set(ctx.tool_names())

    updated: List[SpecV2] = []
    for spec in spec_list:
        if spec.tool_name not in known:
            logger.warning(
                "Skipping examples for '{}': no such tool in the supplied tool set",
                spec.tool_name,
            )
            continue
        await run_examples(
            llm,
            ctx,
            ctx.tool_by_name(spec.tool_name),
            spec.policy_items,
            example_number,
        )
        if rewrite:
            dump_spec(spec, work_dir / f"{spec.tool_name}.json")
        updated.append(spec)

    logger.debug("gen_spec_v2: regenerated examples for {} spec(s)", len(updated))
    return updated


async def generate_guard_specs_v2_full(
    policy_text: str,
    tools: TOOLS_V2,
    llm: I_TG_LLM,
    work_dir: str | Path,
    *,
    system_vars: SystemVarsInput = None,
    source_doc: str = "",
    options: Optional[SpecV2Options] = None,
) -> List[SpecV2]:
    """Generate every tool's spec, then the conflicts across them."""
    specs = await generate_guard_specs_v2(
        policy_text,
        tools,
        llm,
        work_dir,
        system_vars=system_vars,
        source_doc=source_doc,
        options=options,
    )
    return await generate_spec_conflicts_v2(llm, work_dir, specs=specs)
