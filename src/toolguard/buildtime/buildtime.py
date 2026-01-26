import os
from pathlib import Path
from typing import Callable, List, Optional, cast
import logging
from langchain_core.tools import BaseTool

from toolguard.buildtime.utils.open_api import OpenAPI
from toolguard.runtime.data_types import ToolGuardsCodeGenerationResult, ToolGuardSpec
from toolguard.buildtime.llm.i_tg_llm import I_TG_LLM
from toolguard.buildtime.gen_py.gen_toolguards import (
    generate_toolguards_from_functions,
    generate_toolguards_from_openapi,
)
from toolguard.buildtime.langchain_to_oas import langchain_tools_to_openapi
from toolguard.buildtime.data_types import TOOLS
from toolguard.buildtime.gen_spec.spec_generator import extract_toolguard_specs

logger = logging.getLogger(__name__)


# Step1 only
async def generate_guard_specs(
    policy_text: str,
    tools: TOOLS,
    llm: I_TG_LLM,
    work_dir: str | Path,
    tools2guard: List[str] | None = None,
    short=False,
) -> List[ToolGuardSpec]:
    work_dir = Path(work_dir)
    os.makedirs(work_dir, exist_ok=True)

    return await extract_toolguard_specs(
        policy_text, tools, work_dir, llm, tools2guard, short
    )


# Step2 only
async def generate_guards_code(
    tools: TOOLS,
    tool_specs: List[ToolGuardSpec],
    work_dir: str | Path,
    llm: I_TG_LLM,
    app_name: str = "myapp",
    lib_names: Optional[List[str]] = None,
    tool_names: Optional[List[str]] = None,
) -> ToolGuardsCodeGenerationResult:
    tool_specs = [
        policy
        for policy in tool_specs
        if (not tool_names) or (policy.tool_name in tool_names)
    ]
    work_dir = Path(work_dir)
    os.makedirs(work_dir, exist_ok=True)

    # case1: path to OpenAPI spec
    if isinstance(tools, dict):
        oas = OpenAPI.model_validate(tools, strict=False)
        return await generate_toolguards_from_openapi(
            app_name, tool_specs, work_dir, oas, llm
        )

    # case2: List of Langchain tools
    if isinstance(tools, list) and all([isinstance(tool, BaseTool) for tool in tools]):
        oas = langchain_tools_to_openapi(tools)  # type: ignore
        return await generate_toolguards_from_openapi(
            app_name, tool_specs, work_dir, oas, llm
        )

    # Case 3: List of functions/ List of methods
    # TODO List of ToolInfo is not implemented
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
