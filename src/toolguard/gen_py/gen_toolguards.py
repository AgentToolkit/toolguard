import asyncio
import logging
from typing import Callable, List, Optional

import mellea

from .domain_from_funcs import generate_domain_from_functions
from ..data_types import RuntimeDomain, ToolGuardSpec, MelleaSessionData
from .domain_from_openapi import generate_domain_from_openapi
from ..runtime import ToolGuardsCodeGenerationResult
from .tool_guard_generator import ToolGuardGenerator
from .utils import pytest, pyright

logger = logging.getLogger(__name__)

async def generate_toolguards_from_functions(
    app_name: str,
    tool_policies: List[ToolGuardSpec],
    py_root: str,
    funcs: List[Callable],
    llm_data: MelleaSessionData,
    module_roots: Optional[List[str]] = None,
) -> ToolGuardsCodeGenerationResult:
    assert funcs, "Funcs cannot be empty"
    logger.debug(f"Starting... will save into {py_root}")

    if not module_roots:
        if len(funcs) > 0:
            module_roots = list(
                {func.__module__.split(".")[0] for func in funcs}
            )
    assert module_roots

    # Domain from functions
    domain = generate_domain_from_functions(py_root, app_name, funcs, module_roots)
    return await generate_toolguards_from_domain(
        app_name, tool_policies, py_root, domain, llm_data
    )


async def generate_toolguards_from_openapi(
    app_name: str, tool_policies: List[ToolGuardSpec], py_root: str, openapi_file: str, llm_data: MelleaSessionData
) -> ToolGuardsCodeGenerationResult:
    logger.debug(f"Starting... will save into {py_root}")

    # Domain from OpenAPI
    domain = generate_domain_from_openapi(py_root, app_name, openapi_file)
    return await generate_toolguards_from_domain(
        app_name, tool_policies, py_root, domain, llm_data
    )

async def generate_toolguards_from_domain(
    app_name: str, specs: List[ToolGuardSpec], py_root: str, domain: RuntimeDomain,
    llm_data: MelleaSessionData
) -> ToolGuardsCodeGenerationResult:
    # Setup env
    pyright.config(py_root)
    pytest.configure(py_root)

    for tool_policy in specs:
        for policy in tool_policy.policy_items:
            policy.name = policy.name.replace(".","_")

    not_empty_specs = [spec for spec in [
        ToolGuardSpec( #a copy
            tool_name=spec.tool_name, 
            policy_items=[i for i in spec.policy_items if not i.skip])
        for spec in specs
    ] if len(spec.policy_items) > 0]

    mellea_workaround = {"model_options": {"reasoning_effort": "medium"}}#FIXME https://github.com/generative-computing/mellea/issues/270
    kw_args = llm_data.kw_args
    kw_args.update(mellea_workaround)

    m = mellea.start_session(
        backend_name = llm_data.backend_name,
        model_id=llm_data.model_id,
        **kw_args
    )
    tool_results = await asyncio.gather(
        *[
            ToolGuardGenerator(
                app_name, tool_policy, py_root, domain, m
            ).generate()
            for tool_policy in not_empty_specs
        ]
    )

    tools_result = {
        tool.tool_name: res for tool, res in zip(not_empty_specs, tool_results)
    }
    return ToolGuardsCodeGenerationResult(
        out_dir=py_root, 
        domain=domain, 
        tools=tools_result
    ).save(py_root)
