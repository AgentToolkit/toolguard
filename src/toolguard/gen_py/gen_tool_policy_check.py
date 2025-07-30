import asyncio
from os.path import join
from typing import Callable, List, Optional
from loguru import logger
from toolguard.gen_py.gen_domain import APIGenerator
from toolguard.data_types import ToolPolicy
from toolguard.runtime import ToolGuardsCodeGenerationResult
from toolguard.gen_py.tool_guard_generator import ToolGuardGenerator
import toolguard.utils.pyright as pyright
import toolguard.utils.pytest as pytest

import asyncio
from typing import List
from loguru import logger
from toolguard.data_types import ToolPolicy
import toolguard.utils.venv as venv
import toolguard.utils.pyright as pyright

PY_ENV = "my_env"
PY_PACKAGES = ["pydantic", "pytest"]#, "litellm"]

async def generate_tool_guards(app_name: str, tool_policies: List[ToolPolicy], py_root:str, funcs: List[Callable], module_roots: Optional[List[str]]=None)->ToolGuardsCodeGenerationResult:
    if not module_roots:
        if len(funcs)>0:
            module_roots = list({func.__module__.split(".")[0] for func in funcs})
    assert module_roots

    logger.debug(f"Starting... will save into {py_root}")

    #Domain from Open API Spec
    domain = APIGenerator(py_root, app_name, module_roots)\
        .generate_domain(funcs)
    
    #Setup env (slow, hence last):
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
