import inspect
import os
from os.path import join
from pathlib import Path
import shutil
from typing import Any, Callable, Dict, List, Type, TypeVar

import markdown  # type: ignore[import]

import pytest
from toolguard.buildtime import (
    generate_guard_specs,
    generate_guards_from_specs,
    LitellmModel,
)
from toolguard.buildtime.llm.i_tg_llm import I_TG_LLM
from toolguard.runtime import (
    LangchainToolInvoker,
    IToolInvoker,
    ToolMethodsInvoker,
    ToolFunctionsInvoker,
    load_toolguards,
    ToolGuardsCodeGenerationResult,
    PolicyViolationException,
)
from calculator.inputs import tool_langchain as lg_tools
from calculator.inputs import tool_functions as fn_tools

wiki_path = "examples/calculator/inputs/policy_doc.md"
model = "gpt-4o-2024-08-06"
llm_provider = "azure"
app_name = "calc"  # dont use "calculator", as it conflicts with example name
STEP1 = "step1"
STEP2 = "step2"


@pytest.fixture
def llm() -> I_TG_LLM:
    return LitellmModel(
        model_name=os.getenv("MODEL_NAME") or "gpt-4o-2024-08-06",
        provider=os.getenv("LLM_PROVIDER") or "azure",
        kw_args={
            "api_base": os.getenv("LLM_API_BASE"),
            "api_version": os.getenv("LLM_API_VERSION"),
            "api_key": os.getenv("LLM_API_KEY"),
        },
    )


async def _build_toolguards(
    model: str,
    llm: I_TG_LLM,
    work_dir: Path,
    tools: List[Callable] | str,
    app_sufix: str = "",
    short: bool = True,
):
    policy_text = markdown.markdown(open(wiki_path, "r", encoding="utf-8").read())

    run_dir = os.path.join(work_dir, model)  # todo: add timestemp
    shutil.rmtree(run_dir, ignore_errors=True)
    os.makedirs(run_dir, exist_ok=True)
    step1_out_dir = join(run_dir, STEP1)
    step2_out_dir = join(run_dir, STEP2)

    specs = await generate_guard_specs(
        policy_text=policy_text,
        tools=tools,
        work_dir=step1_out_dir,
        llm=llm,
        short=short,
    )
    # spec = ToolGuardSpec.load("examples/calculator/outputs/tool_functions/gpt-4o-2024-08-06/step1/multiply_tool.json")
    guards = await generate_guards_from_specs(
        tool_specs=specs,
        tools=tools,
        work_dir=step2_out_dir,
        llm=llm,
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
        await toolguard.check_toolcall(
            "divide_tool", make_args({"g": 5, "h": 4}), tool_invoker
        )
        await toolguard.check_toolcall(
            "add_tool", make_args({"a": 5, "b": 4}), tool_invoker
        )
        await toolguard.check_toolcall(
            "subtract_tool", make_args({"a": 5, "b": 4}), tool_invoker
        )
        await toolguard.check_toolcall(
            "multiply_tool", make_args({"a": 5, "b": 4}), tool_invoker
        )
        await toolguard.check_toolcall(
            "map_kdi_number", make_args({"i": 5}), tool_invoker
        )

        # test violations
        with pytest.raises(PolicyViolationException):
            await toolguard.check_toolcall(
                "divide_tool", make_args({"g": 5, "h": 0}), tool_invoker
            )

        with pytest.raises(PolicyViolationException):
            await toolguard.check_toolcall(
                "add_tool", make_args({"a": 5, "b": 73}), tool_invoker
            )

        with pytest.raises(PolicyViolationException):
            await toolguard.check_toolcall(
                "add_tool", make_args({"a": 73, "b": 5}), tool_invoker
            )

        # Force to use the kdi_number other tool
        with pytest.raises(PolicyViolationException):
            await toolguard.check_toolcall(
                "multiply_tool", make_args({"a": 2, "b": 73}), tool_invoker
            )

        with pytest.raises(PolicyViolationException):
            await toolguard.check_toolcall(
                "multiply_tool", make_args({"a": 22, "b": 2}), tool_invoker
            )


@pytest.mark.asyncio
async def test_tool_functions_short(llm: I_TG_LLM):
    work_dir = Path("tests/tmp/calculator/tool_functions_short")
    funcs = [
        fn_tools.divide_tool,
        fn_tools.add_tool,
        fn_tools.subtract_tool,
        fn_tools.multiply_tool,
        fn_tools.map_kdi_number,
    ]

    gen_result = await _build_toolguards(
        model, llm, work_dir, funcs, "_fns_short", True
    )
    gen_result = ToolGuardsCodeGenerationResult.load(work_dir / model / STEP2)
    await assert_toolgurards_run(gen_result, ToolFunctionsInvoker(funcs))


@pytest.mark.asyncio
async def test_tool_functions_long(llm: I_TG_LLM):
    work_dir = Path("tests/tmp/calculator/tool_functions_long")
    funcs = [
        fn_tools.divide_tool,
        fn_tools.add_tool,
        fn_tools.subtract_tool,
        fn_tools.multiply_tool,
        fn_tools.map_kdi_number,
    ]

    gen_result = await _build_toolguards(
        model, llm, work_dir, funcs, "_fns_long", False
    )
    gen_result = ToolGuardsCodeGenerationResult.load(work_dir / model / STEP2)
    await assert_toolgurards_run(gen_result, ToolFunctionsInvoker(funcs))


@pytest.mark.asyncio
async def test_tool_methods(llm: I_TG_LLM):
    work_dir = Path("tests/tmp/calculator/tool_methods")
    from calculator.inputs.tool_methods import CalculatorTools

    mtds: List[Callable] = [
        member
        for name, member in inspect.getmembers(
            CalculatorTools, predicate=inspect.isfunction
        )
    ]

    gen_result = await _build_toolguards(model, llm, work_dir, mtds, "_mtds", True)
    gen_result = ToolGuardsCodeGenerationResult.load(work_dir / model / STEP2)
    await assert_toolgurards_run(gen_result, ToolMethodsInvoker(CalculatorTools()))


@pytest.mark.asyncio
async def test_tools_langchain(llm: I_TG_LLM):
    work_dir = Path("tests/tmp/calculator/lg_tools")
    tools = [
        lg_tools.divide_tool,
        lg_tools.add_tool,
        lg_tools.subtract_tool,
        lg_tools.multiply_tool,
        lg_tools.map_kdi_number,
    ]

    gen_result = await _build_toolguards(model, llm, work_dir, tools, "_lg", True)
    gen_result = ToolGuardsCodeGenerationResult.load(work_dir / model / STEP2)

    await assert_toolgurards_run(gen_result, LangchainToolInvoker(tools), True)


@pytest.mark.asyncio
async def test_tools_openapi_spec(llm: I_TG_LLM):
    work_dir = Path("tests/tmp/calculator/oas_tools")
    oas_path = "examples/calculator/inputs/oas.json"

    gen_result = await _build_toolguards(
        model, llm, work_dir, tools=oas_path, app_sufix="_oas", short=True
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
