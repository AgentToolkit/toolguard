from pathlib import Path
from typing import Callable, List, Optional, cast

from loguru import logger

from toolguard.buildtime.data_types import TOOLS
from toolguard.buildtime.gen_py.gen_toolguards import (
    generate_toolguards_from_functions,
    generate_toolguards_from_openapi,
)
from toolguard.buildtime.gen_spec.spec_generator import (
    extract_toolguard_specs,
    PolicySpecOptions,
    ToolGuardSpecGenerator,
    _tools_to_tool_infos,
)
from toolguard.buildtime.gen_spec_v2.data_types import ToolGuardSpecV2
from toolguard.buildtime.gen_spec_v2.spec_generator import (
    PHASE_ONE_STEPS,
    SpecV2Options,
    ToolGuardSpecGeneratorV2,
    tools_to_tool_infos,
)
from toolguard.buildtime.llm import I_TG_LLM
from toolguard.buildtime.utils.open_api import OpenAPI
from toolguard.runtime.data_types import ToolGuardsCodeGenerationResult, ToolGuardSpec


# Step1 only
async def generate_guard_specs(
    policy_text: str,
    tools: TOOLS,
    llm: I_TG_LLM,
    work_dir: str | Path,
    *,
    tools2guard: List[str] | None = None,
    options: Optional[PolicySpecOptions] = None,
) -> List[ToolGuardSpec]:
    """Generate guard specifications from policy text and tools.

    Args:
        policy_text: The policy text describing the guard rules.
        tools: The tools to generate guards for (OpenAPI spec, or functions).
        llm: The LLM instance to use for generation.
        work_dir: The working directory for intermediate files.
        tools2guard: Optional list of specific tool names to generate guards for.


    Returns:
        List of ToolGuardSpec objects containing the generated specifications.
    """
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    logger.debug("Step1 folder created")
    return await extract_toolguard_specs(
        policy_text, tools, work_dir, llm, tools2guard, options
    )


# Step2 only
async def generate_guards_code(
    tools: TOOLS,
    tool_specs: List[ToolGuardSpec],
    work_dir: str | Path,
    llm: I_TG_LLM,
    app_name: str,
    *,
    lib_names: Optional[List[str]] = None,
    tool_names: Optional[List[str]] = None,
) -> ToolGuardsCodeGenerationResult:
    """Generate guard code from tool specifications.

    Args:
        tools: The tools to generate guards for (OpenAPI spec, or functions).
        tool_specs: List of ToolGuardSpec objects containing the guard specifications.
        work_dir: The working directory for intermediate files.
        llm: The LLM instance to use for generation.
        app_name: The application name for the generated code.
        lib_names: Optional list of module root names for function-based tools.
        tool_names: Optional list of specific tool names to generate code for.

    Returns:
        ToolGuardsCodeGenerationResult containing the generated guard code and metadata.

    Raises:
        NotImplementedError: If the tools type is not supported.
    """
    tool_specs = [
        policy
        for policy in tool_specs
        if (not tool_names) or (policy.tool_name in tool_names)
    ]
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    logger.debug("Step2 folder created")
    # OpenAPI spec
    if isinstance(tools, dict):
        oas = OpenAPI.model_validate(tools, strict=False)
        return await generate_toolguards_from_openapi(
            app_name, tool_specs, work_dir, oas, llm
        )

    # List of functions
    if isinstance(tools, list):
        funcs = [cast(Callable, tool) for tool in tools]
        return await generate_toolguards_from_functions(
            app_name,
            tool_specs,
            work_dir,
            funcs=funcs,
            llm=llm,
            module_roots=lib_names,
        )

    raise NotImplementedError()


# Generate examples for existing specs
async def generate_guard_examples(
    tools: TOOLS,
    tool_specs: List[ToolGuardSpec],
    llm: I_TG_LLM,
    work_dir: str | Path,
    *,
    example_number: Optional[int] = None,
) -> List[ToolGuardSpec]:
    """Generate examples for existing tool guard specifications.

    Args:
        tools: The tools to generate examples for (OpenAPI spec, or functions).
        tool_specs: List of ToolGuardSpec objects to generate examples for.
        llm: The LLM instance to use for generation.
        work_dir: The working directory for intermediate files.
        example_number: Number of examples to generate per policy item.
            None = let LLM decide, 0 = no examples, >0 = that many examples.

    Returns:
        List of ToolGuardSpec objects with generated examples added.
    """
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    # Convert tools to tool infos
    tool_infos = _tools_to_tool_infos(tools)

    # Create a generator instance (we don't need policy_document for examples)
    generator = ToolGuardSpecGenerator(
        llm=llm,
        policy_document="",  # Not needed for example generation
        tools=tool_infos,
        out_dir=work_dir,
    )

    # Generate examples for each spec
    for spec in tool_specs:
        await generator.example_creator(
            tool_name=spec.tool_name,
            spec=spec,
            fixed_examples=example_number,
        )

    return tool_specs


# Step1 v2 only: the step1-schema spec format (trigger, requires, pending
# questions, per-tool conflicts). Generation is two phases so policies and
# examples can be produced and reviewed separately; a spec only satisfies the
# step1 schema once examples exist, which is what `_full` guarantees.
async def generate_guard_specs_v2(
    policy_text: str,
    tools: TOOLS,
    llm: I_TG_LLM,
    work_dir: str | Path,
    *,
    system_vars: str | Path | dict | None = None,
    source_doc: str = "policy_document",
    tools2guard: List[str] | None = None,
    options: Optional[SpecV2Options] = None,
) -> List[ToolGuardSpecV2]:
    """Generate v2 guard specs WITHOUT examples (phase 1).

    Args:
        policy_text: The policy document as **markdown**. HTML yields no rules
            and cannot be quoted verbatim, so it is warned about.
        tools: The tools to guard (OpenAPI spec, or callables).
        llm: The LLM instance to use for generation.
        work_dir: Where the per-tool specs are written.
        system_vars: The acting user's variables, as a mapping or a path to JSON.
        source_doc: Path recorded in each spec, which its references quote.
        tools2guard: Optional subset of tool names to generate for.
        options: Stage/vote/concurrency overrides.

    Returns:
        One ToolGuardSpecV2 per tool that carries at least one policy item.
        Written specs are NOT yet schema-valid: every policy item still needs
        examples, added by generate_guard_examples_v2.
    """
    generator = _make_v2_generator(
        policy_text,
        tools,
        llm,
        work_dir,
        system_vars,
        source_doc,
        options,
        steps=PHASE_ONE_STEPS,
    )
    result = await generator.generate_all(tools2guard=tools2guard)
    return list(result.specs.values())


async def generate_guard_specs_v2_full(
    policy_text: str,
    tools: TOOLS,
    llm: I_TG_LLM,
    work_dir: str | Path,
    *,
    system_vars: str | Path | dict | None = None,
    source_doc: str = "policy_document",
    tools2guard: List[str] | None = None,
    options: Optional[SpecV2Options] = None,
) -> List[ToolGuardSpecV2]:
    """Generate v2 guard specs WITH examples: both phases in one call.

    Same arguments as generate_guard_specs_v2. The written specs satisfy the
    step1 schema.
    """
    generator = _make_v2_generator(
        policy_text, tools, llm, work_dir, system_vars, source_doc, options
    )
    result = await generator.generate_all(tools2guard=tools2guard)
    return list(result.specs.values())


async def generate_guard_examples_v2(
    tools: TOOLS,
    specs: List[ToolGuardSpecV2] | str | Path,
    llm: I_TG_LLM,
    work_dir: str | Path,
    *,
    policy_text: str = "",
    system_vars: str | Path | dict | None = None,
    options: Optional[SpecV2Options] = None,
) -> List[ToolGuardSpecV2]:
    """Add compliance/violation examples to existing v2 specs (phase 2).

    Args:
        tools: The tools the specs guard (OpenAPI spec, or callables).
        specs: Specs to complete, or a directory to load them from.
        llm: The LLM instance to use for generation.
        work_dir: Where the completed specs are written.
        policy_text: Optional; unused by this phase beyond prompt context.
        system_vars: The acting user's variables, so examples use real values.
        options: Stage/vote/concurrency overrides.

    Returns:
        One ToolGuardSpecV2 per spec that ended up with examples on every item.
        An item left without them is rejected rather than written invalid.
    """
    generator = _make_v2_generator(
        policy_text, tools, llm, work_dir, system_vars, "policy_document", options
    )
    to_complete = (
        generator.load_specs() if isinstance(specs, (str, Path)) else list(specs)
    )
    result = await generator.add_examples(to_complete)
    return list(result.specs.values())


def _make_v2_generator(
    policy_text: str,
    tools: TOOLS,
    llm: I_TG_LLM,
    work_dir: str | Path,
    system_vars: str | Path | dict | None,
    source_doc: str,
    options: Optional[SpecV2Options],
    steps: set | None = None,
) -> ToolGuardSpecGeneratorV2:
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    options = options or SpecV2Options()
    if steps is not None:
        options = options.model_copy(update={"steps": options.steps & steps})
    return ToolGuardSpecGeneratorV2(
        llm=llm,
        policy_document=policy_text,
        tools=tools_to_tool_infos(tools),
        out_dir=work_dir,
        sys_var=system_vars,
        options=options,
        source_doc=source_doc,
    )
