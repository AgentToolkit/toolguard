import os
from pathlib import Path
from typing import Callable, List, Optional, cast
import json
import logging
from langchain_core.tools import BaseTool

from toolguard.buildtime.data_types import ToolInfo
from toolguard.runtime.data_types import ToolGuardsCodeGenerationResult, ToolGuardSpec
from .llm.i_tg_llm import I_TG_LLM
from .gen_py.gen_toolguards import (
    generate_toolguards_from_functions,
    generate_toolguards_from_openapi,
)
from .oas_to_toolinfo import openapi_to_toolinfos
from .gen_spec.spec_generator import extract_toolguard_specs
from .langchain_to_oas import langchain_tools_to_openapi

logger = logging.getLogger(__name__)

TOOLS = List[Callable] | List[BaseTool] | List[ToolInfo] | str | Path


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

    tools_info = _tools_to_tool_infos(tools, work_dir)
    return await extract_toolguard_specs(
        policy_text, tools_info, work_dir, llm, tools2guard, short
    )


def _tools_to_tool_infos(
    tools: TOOLS,
    work_dir: Path,
) -> List[ToolInfo]:
    # case1: path to OpenAPI spec
    oas_path = Path(tools) if isinstance(tools, str | Path) else None

    # case2: List of Langchain tools
    if isinstance(tools, list) and all([isinstance(tool, BaseTool) for tool in tools]):
        oas = langchain_tools_to_openapi(tools)  # type: ignore
        oas_path = work_dir / "oas.json"
        oas.save(oas_path)

    if oas_path:  # for cases 1 and 2
        with open(oas_path, "r", encoding="utf-8") as file:
            oas = json.load(file)
        return openapi_to_toolinfos(oas)

    # Case 3: List of functions/ List of methods / List of ToolInfos
    if isinstance(tools, list):
        tools_info = []
        for tool in tools:
            if callable(tool):
                tools_info.append(ToolInfo.from_function(cast(Callable, tool)))
            elif isinstance(tool, ToolInfo):
                tools_info.append(tool)
            else:
                raise NotImplementedError()
        return tools_info

    raise NotImplementedError()


# Step2 only
async def generate_guards_from_specs(
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
    oas_path = Path(tools) if isinstance(tools, str) else None

    # case2: List of Langchain tools
    if isinstance(tools, list) and all([isinstance(tool, BaseTool) for tool in tools]):
        oas = langchain_tools_to_openapi(tools)  # type: ignore
        oas_path = work_dir / "oas.json"
        oas.save(oas_path)

    if oas_path:  # for cases 1 and 2
        return await generate_toolguards_from_openapi(
            app_name, tool_specs, work_dir, oas_path, llm
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
