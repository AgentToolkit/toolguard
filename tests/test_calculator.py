import inspect
import os
from os.path import join
import shutil
from typing import Any, Callable, Dict, List, Type, TypeVar

import markdown

import pytest
from toolguard import IToolInvoker, ToolFunctionsInvoker, ToolGuardsCodeGenerationResult, ToolMethodsInvoker, load_toolguard_code_result, load_toolguards
from toolguard import LitellmModel
from toolguard.buildtime import build_toolguards
from toolguard.data_types import MeleaSessionData
from toolguard.runtime import LangchainToolInvoker

wiki_path = "examples/calculator/inputs/policy_doc.md"
model = "gpt-4o-2024-08-06"
llm_provider = "azure"
app_name = "calc" # dont use "calculator", as it conflicts with example name
STEP1 = "step1"
STEP2 = "step2"

step1_llm = LitellmModel(model, llm_provider)
step2_llm = MeleaSessionData()#initialized from env vars

async def _build_toolguards(
    model:str,
    work_dir: str,
    tools: List[Callable]| str,
    app_sufix: str = ""
):
    policy_text = markdown.markdown(open(wiki_path, 'r', encoding='utf-8').read())
    
    run_dir = os.path.join(work_dir, model) #todo: add timestemp
    shutil.rmtree(run_dir, ignore_errors=True);
    os.makedirs(run_dir, exist_ok=True)
    step1_out_dir = join(run_dir, STEP1)
    step2_out_dir = join(run_dir, STEP2)

    return await build_toolguards(
		policy_text = policy_text, 
		tools = tools, 
		step1_out_dir = step1_out_dir, 
		step2_out_dir = step2_out_dir, 
		step1_llm = step1_llm,
        step2_llm=step2_llm,
		app_name= app_name+app_sufix, 
		# tools2run = [], 
		short1=True
    )

def assert_toolgurards_run(gen_result: ToolGuardsCodeGenerationResult, tool_invoker: IToolInvoker, openapi_spec = False):
    def make_args(args):
        if openapi_spec:
            return {"args": args}
        return args
    
    with load_toolguards(gen_result.out_dir) as toolguard:
        from rt_toolguard.data_types import PolicyViolationException

        #test compliance
        toolguard.check_toolcall("divide_tool", make_args({"g": 5, "h": 4}), tool_invoker)
        toolguard.check_toolcall("add_tool", make_args({"a": 5, "b": 4}), tool_invoker)
        toolguard.check_toolcall("subtract_tool", make_args({"a": 5, "b": 4}), tool_invoker)
        toolguard.check_toolcall("multiply_tool", make_args({"a": 5, "b": 4}), tool_invoker)
        toolguard.check_toolcall("map_kdi_number", make_args({"i": 5}), tool_invoker)
        
        #test violations
        with pytest.raises(PolicyViolationException):
            toolguard.check_toolcall("divide_tool", make_args({"g": 5, "h": 0}), tool_invoker)

        with pytest.raises(PolicyViolationException):
            toolguard.check_toolcall("add_tool", make_args({"a": 5, "b": 73}), tool_invoker)

        with pytest.raises(PolicyViolationException):
            toolguard.check_toolcall("add_tool", make_args({"a": 73, "b": 5}), tool_invoker)

        #Force to use the kdi_number other tool
        with pytest.raises(PolicyViolationException):
            toolguard.check_toolcall("multiply_tool", make_args({"a": 2, "b": 73}), tool_invoker)

        with pytest.raises(PolicyViolationException):
            toolguard.check_toolcall("multiply_tool", make_args({"a": 22, "b": 2}), tool_invoker)


from calculator.inputs import tool_functions as fn_tools
@pytest.mark.asyncio
async def test_tool_functions():
    work_dir = "examples/calculator/outputs/tool_functions"
    funcs = [fn_tools.divide_tool, fn_tools.add_tool, fn_tools.subtract_tool, fn_tools.multiply_tool, fn_tools.map_kdi_number]

    gen_result = await _build_toolguards(model, work_dir, funcs, "_fns")
    gen_result = load_toolguard_code_result(join(work_dir, model, STEP2))
    assert_toolgurards_run(gen_result, ToolFunctionsInvoker(funcs))

@pytest.mark.asyncio
async def test_tool_methods():
    work_dir = "examples/calculator/outputs/tool_methods"
    from calculator.inputs.tool_methods import CalculatorTools
    mtds = [member for name, member in inspect.getmembers(CalculatorTools, predicate=inspect.isfunction)]

    gen_result = await _build_toolguards(model, work_dir, mtds, "_mtds")
    gen_result = load_toolguard_code_result(join(work_dir, model, STEP2))
    assert_toolgurards_run(gen_result, ToolMethodsInvoker(CalculatorTools()))

from calculator.inputs import tool_langchain as lg_tools
@pytest.mark.asyncio
async def test_tools_langchain():
    work_dir = "examples/calculator/outputs/lg_tools"
    tools = [lg_tools.divide_tool, lg_tools.add_tool, lg_tools.subtract_tool, lg_tools.multiply_tool, lg_tools.map_kdi_number]

    gen_result = await _build_toolguards(model, work_dir, tools, "_lg")
    gen_result = load_toolguard_code_result(join(work_dir, model, STEP2))

    assert_toolgurards_run(gen_result, LangchainToolInvoker(tools), True)

@pytest.mark.asyncio
async def test_tools_openapi_spec():
    work_dir = "examples/calculator/outputs/oas_tools"
    oas_path = "examples/calculator/inputs/oas.json"
    
    gen_result = await _build_toolguards(model, work_dir, tools=oas_path, app_sufix="_oas")
    gen_result = load_toolguard_code_result(join(work_dir, model, STEP2))

    #instead of calling a remote web method, compute inline
    class DummyInvoker(IToolInvoker):
        T = TypeVar("T")
        def __init__(self) -> None:
            funcs = [fn_tools.divide_tool, fn_tools.add_tool, fn_tools.subtract_tool, fn_tools.multiply_tool, fn_tools.map_kdi_number]
            self._funcs_by_name = {func.__name__: func for func in funcs}

        def invoke(self, toolname: str, arguments: Dict[str, Any], return_type: Type[T])->T:
            func = self._funcs_by_name.get(toolname)
            assert callable(func), f"Tool {toolname} was not found"
            return func(**arguments)

    assert_toolgurards_run(gen_result, DummyInvoker(), True)
