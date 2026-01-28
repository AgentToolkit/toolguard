from pathlib import Path
from typing import Callable, List, Optional, cast

from loguru import logger

from toolguard.buildtime.data_types import TOOLS
from toolguard.buildtime.gen_py.gen_toolguards import (
    generate_toolguards_from_functions,
    generate_toolguards_from_openapi,
)
from toolguard.buildtime.gen_spec.spec_generator import extract_toolguard_specs
from toolguard.buildtime.llm.i_tg_llm import I_TG_LLM
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
    short: bool = False,
) -> List[ToolGuardSpec]:
    """Generate guard specifications from policy text and tools.

    Args:
        policy_text: The policy text describing the guard rules.
        tools: The tools to generate guards for (OpenAPI spec, or functions).
        llm: The LLM instance to use for generation.
        work_dir: The working directory for intermediate files.
        tools2guard: Optional list of specific tool names to generate guards for.
        short: Whether to use a short generation process, less accurate (default: False).

    Returns:
        List of ToolGuardSpec objects containing the generated specifications.
    """
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    logger.debug("Step1 folder created")
    return await extract_toolguard_specs(
        policy_text, tools, work_dir, llm, tools2guard, short
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
