import asyncio
import logging
import json
from os.path import join
from typing import Callable, List, Optional

from toolguard.gen_py.consts import *
from toolguard.gen_py.domain_from_funcs import generate_domain_from_functions
from toolguard.data_types import RuntimeDomain, ToolPolicy, FileTwin
from toolguard.gen_py.domain_from_openapi import generate_domain_from_openapi
from toolguard.runtime import ToolGuardsCodeGenerationResult
from toolguard.gen_py.tool_guard_generator import ToolGuardGenerator
import toolguard.utils.pytest as pytest
import toolguard.utils.venv as venv
import toolguard.utils.pyright as pyright

logger = logging.getLogger(__name__)

async def generate_toolguards_from_functions(app_name: str, tool_policies: List[ToolPolicy], py_root:str, funcs: List[Callable], module_roots: Optional[List[str]]=None)->ToolGuardsCodeGenerationResult:
    assert funcs, "Funcs cannot be empty"
    logger.debug(f"Starting... will save into {py_root}")

    if not module_roots:
        if len(funcs)>0:
            module_roots = list({func.__module__.split(".")[0] for func in funcs})
    assert module_roots

    #Domain from functions
    domain = generate_domain_from_functions(py_root, app_name, funcs, module_roots)
    return await generate_toolguards_from_domain(app_name, tool_policies, py_root, domain)

async def generate_toolguards_from_openapi(app_name: str, tool_policies: List[ToolPolicy], py_root:str, openapi_file:str)->ToolGuardsCodeGenerationResult:
    logger.debug(f"Starting... will save into {py_root}")

    #Domain from OpenAPI
    domain = generate_domain_from_openapi(py_root, app_name, openapi_file)
    return await generate_toolguards_from_domain(app_name, tool_policies, py_root, domain)

async def generate_toolguards_from_domain(app_name: str, tool_policies: List[ToolPolicy], py_root:str, domain: RuntimeDomain)->ToolGuardsCodeGenerationResult:
    #Save policies in folder
    FileTwin(
        file_name="policies.json", 
        content=json.dumps([tool_policy.model_dump() for tool_policy in tool_policies], indent=2))\
            .save(py_root)

    #Setup env
    venv.run(join(py_root, PY_ENV), PY_PACKAGES)
    pyright.config(py_root)
    pytest.configure(py_root)
    
    #tools
    tools_w_poilicies = [tool_policy for tool_policy in tool_policies if len(tool_policy.policy_items) > 0]
    tool_results = await asyncio.gather(*[
        ToolGuardGenerator(app_name, tool_policy, py_root, domain, PY_ENV)\
            .generate()
        for tool_policy in tools_w_poilicies
    ])

    tools_result = {tool.tool_name: res 
        for tool, res 
        in zip(tools_w_poilicies, tool_results)
    }        
    return ToolGuardsCodeGenerationResult(
        domain=domain,
        tools=tools_result
    ).save(py_root)
