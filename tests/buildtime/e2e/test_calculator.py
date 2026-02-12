import os
import shutil
from os.path import join
from pathlib import Path
from typing import Any, Dict, Type, TypeVar, Optional

import markdown  # type: ignore[import]
import pytest
from examples.calculator.inputs import tool_functions as fn_tools
from examples.calculator.inputs import tool_langchain as lg_tools
from examples.calculator.inputs import tool_methods as mtd_tools
from toolguard.buildtime.gen_spec.spec_generator import (
    PolicySpecOptions,
    PolicySpecStep,
)
from toolguard.buildtime import LitellmModel, generate_guard_specs, generate_guards_code
from toolguard.buildtime.data_types import TOOLS
from toolguard.buildtime.llm import I_TG_LLM
from toolguard.buildtime.utils.open_api import OpenAPI
from toolguard.extra.api_to_functions import api_cls_to_functions
from toolguard.extra.langchain_to_oas import langchain_tools_to_openapi
from toolguard.runtime import (
    IToolInvoker,
    LangchainToolInvoker,
    PolicyViolationException,
    ToolFunctionsInvoker,
    ToolGuardsCodeGenerationResult,
    ToolMethodsInvoker,
    load_toolguards,
)

wiki_path = "tests/examples/calculator/inputs/policy_doc.md"
model = os.getenv("MODEL_NAME") or "gpt-4o-2024-08-06"
llm_provider = "azure"
app_name = "calc"  # dont use "calculator", as it conflicts with example name
STEP1 = "step1"
STEP2 = "step2"

short_options = PolicySpecOptions(
    spec_steps={PolicySpecStep.CREATE_POLICIES},
)


def llm() -> I_TG_LLM:
    return LitellmModel(
        model_name=model,
        provider=os.getenv("LLM_PROVIDER") or "azure",
        kw_args={
            "api_base": os.getenv("LLM_API_BASE"),
            "api_version": os.getenv("LLM_API_VERSION"),
            "api_key": os.getenv("LLM_API_KEY"),
        },
    )


async def _build_toolguards(
    work_dir: Path,
    tools: TOOLS,
    app_sufix: str = "",
    options: Optional[PolicySpecOptions] = None,
):
    policy_text = markdown.markdown(open(wiki_path, "r", encoding="utf-8").read())

    run_dir = work_dir / model
    shutil.rmtree(run_dir, ignore_errors=True)
    os.makedirs(run_dir, exist_ok=True)
    step1_out_dir = join(run_dir, STEP1)
    step2_out_dir = join(run_dir, STEP2)

    specs = await generate_guard_specs(
        policy_text=policy_text,
        tools=tools,
        work_dir=step1_out_dir,
        llm=llm(),
        options=options,
    )
    # spec = ToolGuardSpec.load("/Users/davidboaz/Documents/GitHub/toolguard/tests/tmp/e2e/calculator/tool_functions_short/GCP/claude-4-sonnet/step1/divide_tool.json")
    # specs = [spec]
    guards = await generate_guards_code(
        tool_specs=specs,
        tools=tools,
        work_dir=step2_out_dir,
        llm=llm(),
        app_name=app_name + app_sufix,
    )
    return guards


async def assert_toolgurards_run(
    gen_result: ToolGuardsCodeGenerationResult,
    tool_invoker: IToolInvoker,
    openapi_spec=False,
):
    def make_args(args):
        if openapi_spec:
            return {"args": args}
        return args

    with load_toolguards(gen_result.out_dir) as toolguard:
        # test compliance
        await toolguard.guard_toolcall(
            "divide_tool", make_args({"g": 5, "h": 4}), tool_invoker
        )
        await toolguard.guard_toolcall(
            "add_tool", make_args({"a": 5, "b": 4}), tool_invoker
        )
        await toolguard.guard_toolcall(
            "subtract_tool", make_args({"a": 5, "b": 4}), tool_invoker
        )
        await toolguard.guard_toolcall(
            "multiply_tool", make_args({"a": 5, "b": 4}), tool_invoker
        )
        await toolguard.guard_toolcall(
            "map_kdi_number", make_args({"i": 5}), tool_invoker
        )

        # test violations
        with pytest.raises(PolicyViolationException):
            await toolguard.guard_toolcall(
                "divide_tool", make_args({"g": 5, "h": 0}), tool_invoker
            )

        with pytest.raises(PolicyViolationException):
            await toolguard.guard_toolcall(
                "add_tool", make_args({"a": 5, "b": 73}), tool_invoker
            )

        with pytest.raises(PolicyViolationException):
            await toolguard.guard_toolcall(
                "add_tool", make_args({"a": 73, "b": 5}), tool_invoker
            )

        # Force to use the kdi_number other tool
        with pytest.raises(PolicyViolationException):
            await toolguard.guard_toolcall(
                "multiply_tool", make_args({"a": 2, "b": 73}), tool_invoker
            )

        with pytest.raises(PolicyViolationException):
            await toolguard.guard_toolcall(
                "multiply_tool", make_args({"a": 22, "b": 2}), tool_invoker
            )


@pytest.mark.asyncio
async def test_tool_functions_short():
    work_dir = Path("tests/tmp/e2e/calculator/tool_functions_short")
    funcs = [
        fn_tools.divide_tool,
        fn_tools.add_tool,
        fn_tools.subtract_tool,
        fn_tools.multiply_tool,
        fn_tools.map_kdi_number,
    ]

    gen_result = await _build_toolguards(work_dir, funcs, "_fns_short", short_options)
    gen_result = ToolGuardsCodeGenerationResult.load(work_dir / model / STEP2)
    await assert_toolgurards_run(gen_result, ToolFunctionsInvoker(funcs))


@pytest.mark.asyncio
async def test_tool_methods():
    work_dir = Path("tests/tmp/e2e/calculator/tool_methods")
    fns = api_cls_to_functions(mtd_tools.CalculatorTools)

    gen_result = await _build_toolguards(work_dir, fns, "_mtds", short_options)
    gen_result = ToolGuardsCodeGenerationResult.load(work_dir / model / STEP2)
    await assert_toolgurards_run(
        gen_result, ToolMethodsInvoker(mtd_tools.CalculatorTools())
    )


@pytest.mark.asyncio
async def test_tools_langchain():
    work_dir = Path("tests/tmp/e2e/calculator/lg_tools")
    tools = [
        lg_tools.divide_tool,
        lg_tools.add_tool,
        lg_tools.subtract_tool,
        lg_tools.multiply_tool,
        lg_tools.map_kdi_number,
    ]
    oas = langchain_tools_to_openapi(tools)

    gen_result = await _build_toolguards(work_dir, oas, "_lg", short_options)
    gen_result = ToolGuardsCodeGenerationResult.load(work_dir / model / STEP2)

    await assert_toolgurards_run(gen_result, LangchainToolInvoker(tools), True)


@pytest.mark.asyncio
async def test_tools_openapi_spec():
    work_dir = Path("tests/tmp/e2e/calculator/oas_tools")
    oas_path = "tests/examples/calculator/inputs/oas.json"
    oas = OpenAPI.load_from(oas_path)
    gen_result = await _build_toolguards(
        work_dir, tools=oas.model_dump(), app_sufix="_oas", options=short_options
    )
    gen_result = ToolGuardsCodeGenerationResult.load(work_dir / model / STEP2)

    # instead of calling a remote web method, compute inline
    class DummyInvoker(IToolInvoker):
        T = TypeVar("T")

        def __init__(self) -> None:
            funcs = [
                fn_tools.divide_tool,
                fn_tools.add_tool,
                fn_tools.subtract_tool,
                fn_tools.multiply_tool,
                fn_tools.map_kdi_number,
            ]
            self._funcs_by_name = {func.__name__: func for func in funcs}

        async def invoke(
            self, toolname: str, arguments: Dict[str, Any], return_type: Type[T]
        ) -> T:
            func = self._funcs_by_name.get(toolname)
            assert callable(func), f"Tool {toolname} was not found"
            return func(**arguments)

    await assert_toolgurards_run(gen_result, DummyInvoker(), True)
