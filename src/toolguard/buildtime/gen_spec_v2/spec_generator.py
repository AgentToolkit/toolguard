"""Orchestration: policy rules plus tools in, one spec file per guarded tool out.

Generation is two phases, deliberately separable so they can be run and reviewed
independently:

* **Phase 1 -- policies.** Per tool: create, expand, review, enrich. Then, across
  the run: repair references, find and route conflicts, write the specs.
  Phase-1 output is knowingly NOT schema-valid, because every policy item needs
  at least one compliance and one violation example.
* **Phase 2 -- examples.** :meth:`ToolGuardSpecGeneratorV2.add_examples` fills
  those in and makes the output valid.

Per-tool work is bounded by a semaphore and isolated: one tool's failure is
recorded and the rest of the run continues, which matters on a 30-tool benchmark
where a single unparseable response would otherwise cost everything.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Union, cast

from loguru import logger
from pydantic import BaseModel, Field

from toolguard.buildtime.compat.strenum import StrEnum
from toolguard.buildtime.data_types import TOOLS
from toolguard.buildtime.gen_spec.data_types import ToolInfo
from toolguard.buildtime.gen_spec.fn_to_toolinfo import function_to_toolInfo
from toolguard.buildtime.gen_spec.oas_to_toolinfo import openapi_to_toolinfos
from toolguard.buildtime.gen_spec_v2.conflicts import find_conflicts, split_and_attach
from toolguard.buildtime.gen_spec_v2.context import GenContext
from toolguard.buildtime.gen_spec_v2.data_types import (
    PolicyItemV2,
    RejectedItem,
    ToolGuardSpecV2,
    dump_spec,
    load_spec,
)
from toolguard.buildtime.gen_spec_v2.inputs import (
    PolicyRule,
    extract_policy_rules,
    load_system_vars,
)
from toolguard.buildtime.gen_spec_v2.refmatch import repair_references
from toolguard.buildtime.gen_spec_v2.stages.create import run_create
from toolguard.buildtime.gen_spec_v2.stages.enrich import run_enrich
from toolguard.buildtime.gen_spec_v2.stages.examples import run_examples
from toolguard.buildtime.gen_spec_v2.stages.expand import run_expand
from toolguard.buildtime.gen_spec_v2.stages.review import run_review
from toolguard.buildtime.gen_spec_v2.utils import write_json
from toolguard.buildtime.llm import I_TG_LLM
from toolguard.buildtime.utils.open_api import OpenAPI

#: Non-spec run artifacts live here, never beside the specs: consumers glob
#: ``work_dir/*.json`` for tools, so a stray file there reads as a phantom tool.
PROCESS_DIRNAME = "process"
REJECTED_FILENAME = "rejected.json"
REFERENCES_STAGE = "references"
NO_REFERENCE_REASON = "no reference could be matched to the policy document"


class SpecV2Step(StrEnum):
    """Optional stages. ``create`` always runs -- without it there is nothing."""

    EXPAND = "EXPAND"
    REVIEW = "REVIEW"
    ENRICH = "ENRICH"
    EXAMPLES = "EXAMPLES"
    CONFLICTS = "CONFLICTS"


#: Phase 1 -- everything except examples. Output is not schema-valid until phase
#: 2 has run, since every policy item needs at least one example of each kind.
PHASE_ONE_STEPS: Set[SpecV2Step] = set(SpecV2Step) - {SpecV2Step.EXAMPLES}


class SpecV2Options(BaseModel):
    steps: Set[SpecV2Step] = Field(default_factory=lambda: set(SpecV2Step))
    add_iterations: int = Field(
        default=3,
        description="Maximum expand passes; stops early when one adds nothing",
    )
    review_votes: int = Field(default=5, description="Relevance votes per item")
    feasibility_votes: int = Field(default=3, description="Enrich votes per item")
    max_concurrency: int = Field(default=8, description="Tools processed at once")


class GenerateV2Result(BaseModel):
    """What a run produced: the specs written, and what did not make it."""

    specs: Dict[str, ToolGuardSpecV2] = Field(default_factory=dict)
    written: List[Path] = Field(default_factory=list)
    failed: Dict[str, str] = Field(default_factory=dict)
    rejected: Dict[str, List[RejectedItem]] = Field(default_factory=dict)


class ToolGuardSpecGeneratorV2:
    def __init__(
        self,
        llm: I_TG_LLM,
        policy_document: str,
        tools: List[ToolInfo],
        out_dir: Path,
        sys_var: Optional[Union[str, Path, Dict[str, Any]]] = None,
        options: Optional[SpecV2Options] = None,
        source_doc: str = "policy_document",
    ) -> None:
        self.llm = llm
        self.policy_document = policy_document
        self.tools = list(tools)
        self.tools_by_name = {tool.name: tool for tool in self.tools}
        self.out_dir = Path(out_dir)
        self.source_doc = source_doc
        self.options = options or SpecV2Options()

        # Raises HtmlPolicyDocumentError on rendered HTML: failing here costs
        # nothing, where carrying on costs a model call per tool and writes no
        # specs at all.
        rules = extract_policy_rules(policy_document)
        if not rules:
            logger.warning(
                "No policy rules were found in the document: nothing is bound by "
                "a '- ' or '* ' bullet, so no policy items can be grounded."
            )
        self.policy_rules: List[PolicyRule] = rules
        self.ctx = GenContext(
            policy_rules=rules,
            system_vars=load_system_vars(sys_var),
            tools=self.tools,
        )

    # --- phase 1 ------------------------------------------------------------

    async def generate_policy(
        self, tool_name: str
    ) -> tuple[List[PolicyItemV2], List[RejectedItem]]:
        """Run one tool's stages, returning its surviving items and its rejects."""
        tool = self.tools_by_name[tool_name]
        steps = self.options.steps
        rejected: List[RejectedItem] = []

        metadata, items = await run_create(self.llm, self.ctx, tool)
        logger.debug(
            f"create({tool_name}): {len(items)} item(s), "
            f"read_only={metadata.is_read_only}"
        )

        if SpecV2Step.EXPAND in steps:
            items = await run_expand(
                self.llm, self.ctx, tool, items, self.options.add_iterations
            )

        if SpecV2Step.REVIEW in steps and items:
            items, review_rejects = await run_review(
                self.llm, self.ctx, tool, items, self.options.review_votes
            )
            rejected.extend(review_rejects)

        if SpecV2Step.ENRICH in steps and items:
            await run_enrich(
                self.llm,
                self.ctx,
                tool,
                items,
                self.options.feasibility_votes,
                declared_system_vars=self.ctx.system_vars.names,
            )

        if SpecV2Step.EXAMPLES in steps and items:
            items, example_rejects = await run_examples(self.llm, self.ctx, tool, items)
            rejected.extend(example_rejects)

        return items, rejected

    async def generate_all(
        self, tools2guard: Optional[List[str]] = None
    ) -> GenerateV2Result:
        """Generate every tool's spec (or just the named ones) and write them out."""
        targets = self._targets(tools2guard)
        semaphore = asyncio.Semaphore(self.options.max_concurrency)
        result = GenerateV2Result()

        async def guarded(tool_name: str):
            async with semaphore:
                try:
                    items, rejected = await self.generate_policy(tool_name)
                    return tool_name, items, rejected, None
                except Exception as exc:  # per-tool isolation is the point
                    logger.error(f"{tool_name}: generation failed: {exc}")
                    return tool_name, None, [], str(exc)

        for tool_name, items, rejected, error in await asyncio.gather(
            *(guarded(name) for name in targets)
        ):
            if error is not None:
                result.failed[tool_name] = error
                continue
            if rejected:
                result.rejected.setdefault(tool_name, []).extend(rejected)
            result.specs[tool_name] = ToolGuardSpecV2(
                tool_name=tool_name,
                source_doc=self.source_doc,
                policy_items=cast(List[PolicyItemV2], items),
            )

        self._repair_references(result)
        if SpecV2Step.CONFLICTS in self.options.steps:
            raw_conflicts = await find_conflicts(self.llm, result.specs)
            split_and_attach(result.specs, raw_conflicts)

        self._finish(result)
        return result

    # --- phase 2 ------------------------------------------------------------

    async def add_examples(self, specs: Sequence[ToolGuardSpecV2]) -> GenerateV2Result:
        """Fill in every item's examples and rewrite the specs. Phase 2, standalone.

        A spec whose tool is unknown to this run is skipped rather than guessed
        at -- examples are written against the tool's parameters, so the wrong
        tool would produce plausible nonsense.
        """
        result = GenerateV2Result()

        async def guarded(spec: ToolGuardSpecV2):
            tool = self.tools_by_name.get(spec.tool_name)
            if tool is None:
                return spec.tool_name, None, [], f"unknown tool: {spec.tool_name}"
            try:
                items, rejected = await run_examples(
                    self.llm, self.ctx, tool, spec.policy_items
                )
                return spec.tool_name, items, rejected, None
            except Exception as exc:
                logger.error(f"{spec.tool_name}: examples failed: {exc}")
                return spec.tool_name, None, [], str(exc)

        by_name = {spec.tool_name: spec for spec in specs}
        semaphore = asyncio.Semaphore(self.options.max_concurrency)

        async def bounded(spec: ToolGuardSpecV2):
            async with semaphore:
                return await guarded(spec)

        for tool_name, items, rejected, error in await asyncio.gather(
            *(bounded(spec) for spec in specs)
        ):
            if error is not None:
                result.failed[tool_name] = error
                continue
            if rejected:
                result.rejected.setdefault(tool_name, []).extend(rejected)
            spec = by_name[tool_name]
            spec.policy_items = cast(List[PolicyItemV2], items)
            result.specs[tool_name] = spec

        self._finish(result)
        return result

    def load_specs(self) -> List[ToolGuardSpecV2]:
        """Load the specs already in ``out_dir``, ignoring run artifacts."""
        return [load_spec(path) for path in sorted(self.out_dir.glob("*.json"))]

    # --- shared -------------------------------------------------------------

    def _targets(self, tools2guard: Optional[List[str]]) -> List[str]:
        if tools2guard is None:
            return [tool.name for tool in self.tools]
        unknown = [name for name in tools2guard if name not in self.tools_by_name]
        if unknown:
            raise ValueError(f"unknown tool(s): {', '.join(unknown)}")
        return list(tools2guard)

    def _repair_references(self, result: GenerateV2Result) -> None:
        """Make every reference a verbatim quote; reject the items left with none."""
        for tool_name, spec in result.specs.items():
            emptied = repair_references(
                spec.policy_items, self.policy_document, self.policy_rules
            )
            if not emptied:
                continue
            emptied_ids = {item.id for item in emptied}
            spec.policy_items = [
                item for item in spec.policy_items if item.id not in emptied_ids
            ]
            result.rejected.setdefault(tool_name, []).extend(
                RejectedItem(
                    item=item, reason=NO_REFERENCE_REASON, stage=REFERENCES_STAGE
                )
                for item in emptied
            )

    def _finish(self, result: GenerateV2Result) -> None:
        """Write every spec that carries a rule, then the rejection report.

        A tool with no surviving policy item gets no file: the absence of a spec
        is how "nothing here needs guarding" is spelled.
        """
        self.out_dir.mkdir(parents=True, exist_ok=True)
        for tool_name in sorted(result.specs):
            spec = result.specs[tool_name]
            if not spec.policy_items:
                logger.debug(f"{tool_name}: no policy items, writing no spec")
                continue
            path = self.out_dir / f"{tool_name}.json"
            dump_spec(spec, path)
            result.written.append(path)

        result.specs = {
            name: spec for name, spec in result.specs.items() if spec.policy_items
        }

        write_json(
            self.out_dir / PROCESS_DIRNAME / REJECTED_FILENAME,
            {
                tool_name: [reject.to_dict() for reject in rejects]
                for tool_name, rejects in sorted(result.rejected.items())
            },
        )


def tools_to_tool_infos(tools: TOOLS) -> List[ToolInfo]:
    """Accept what toolguard accepts: an OpenAPI dict or a list of callables."""
    if isinstance(tools, dict):
        return openapi_to_toolinfos(OpenAPI.model_validate(tools))
    if isinstance(tools, list):
        infos: List[ToolInfo] = []
        for tool in tools:
            if isinstance(tool, ToolInfo):
                infos.append(tool)
            elif callable(tool):
                infos.append(function_to_toolInfo(cast(Callable, tool)))
            else:
                raise NotImplementedError(f"unsupported tool entry: {tool!r}")
        return infos
    raise NotImplementedError(f"unsupported tools input: {type(tools).__name__}")
