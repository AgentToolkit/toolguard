import inspect
import json
import os
from os.path import join
import shutil
from typing import Any, Callable, Dict, List, Type, TypeVar

import markdown

import pytest
from toolguard import generate_guards_from_tool_policies_oas, generate_guards_from_tool_policies, extract_policies
from toolguard import IToolInvoker, ToolFunctionsInvoker, ToolGuardsCodeGenerationResult, ToolMethodsInvoker, load_toolguard_code_result, load_toolguards
from toolguard import LitellmModel, load_functions_in_file, ToolInfo
from toolguard.gen_spec.oas_summary import OASSummarizer

wiki_path = "examples/calculator/inputs/policy_doc.md"
model = "gpt-4o-2024-08-06"
app_name = "calc" # dont use "calculator", as it conflicts with example name
STEP1 = "step1"
STEP2 = "step2"

async def build_calculator(
    model:str,
    work_dir: str,
    tools: List[Callable]| str
):
    policy_text = markdown.markdown(open(wiki_path, 'r', encoding='utf-8').read())
    llm = LitellmModel(model, "azure")
    run_dir = os.path.join(work_dir, model) #todo: add timestemp
    shutil.rmtree(run_dir, ignore_errors=True);
    os.makedirs(run_dir, exist_ok=True)
    
    # step1
    step1_out_dir = join(run_dir, STEP1)
    oas_path = tools if isinstance(tools, str) else None
    
    if oas_path:
        with open(oas_path, 'r', encoding='utf-8') as file:
            oas = json.load(file)
        tools_info = OASSummarizer(oas).summarize()
    else:
        tools_info = [ToolInfo.from_function(tool) for tool in tools] # type: ignore
    tool_policies = await extract_policies(policy_text, tools_info, step1_out_dir, llm, None, True)
    
    #step2
    step2_out_dir = join(run_dir, STEP2)
    if oas_path: #path to open api spec file
        return await generate_guards_from_tool_policies_oas(oas_path, tool_policies, step2_out_dir, app_name, None)
    else:
        return await generate_guards_from_tool_policies(tools, tool_policies, step2_out_dir, app_name, None, None) # type: ignore
    

def run_calculator(gen_result: ToolGuardsCodeGenerationResult, tool_invoker: IToolInvoker, openapi_spec = False):
    def make_args(args):
        if openapi_spec:
            return {"args": args}
        return args
    
    with load_toolguards(gen_result.root_dir) as toolguard:
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


@pytest.mark.asyncio
async def test_calculator_callable():
    work_dir = "examples/calculator/outputs/callable"
    app_path = "examples/calculator/inputs"
    app_tools_file = "callable_tools.py"
    funcs = load_functions_in_file(app_path, app_tools_file)

    gen_result = await build_calculator(model, work_dir, funcs)
    run_calculator(gen_result, ToolFunctionsInvoker(funcs))

@pytest.mark.asyncio
async def test_calculator_class_of_tools():
    work_dir = "examples/calculator/outputs/class_of_tools"
    from calculator.inputs.class_tools import CalculatorTools
    mtds = [member for name, member in inspect.getmembers(CalculatorTools, predicate=inspect.isfunction)]

    gen_result = await build_calculator(model, work_dir, mtds)
    # gen_result = load_toolguard_code_result(join(work_dir, model, STEP2))
    run_calculator(gen_result, ToolMethodsInvoker(CalculatorTools()))

@pytest.mark.asyncio
async def test_calculator_langgraph():
    work_dir = "examples/calculator/outputs/lg_tools"
    app_path = "examples/calculator/inputs"
    app_tools_file = "langgraph_tools.py"
    tools = load_functions_in_file(app_path, app_tools_file)

    gen_result = await build_calculator(model, work_dir, tools)
    gen_result = load_toolguard_code_result(join(work_dir, model, STEP2))

    run_calculator(gen_result, ToolFunctionsInvoker(tools))

@pytest.mark.asyncio
async def test_calculator_openapi_spec():
    work_dir = "examples/calculator/outputs/oas"
    oas_path = "examples/calculator/inputs/oas.json"
    
    await build_calculator(model, work_dir, tools=oas_path)
    gen_result = load_toolguard_code_result(join(work_dir, model, STEP2))

    #instead of calling a remote web method, compute inline
    callable_path = "callable_tools.py"
    app_path = "examples/calculator/inputs"
    class DummyInvoker(IToolInvoker):
        T = TypeVar("T")
        def __init__(self) -> None:
            funcs = load_functions_in_file(app_path, callable_path)
            self._funcs_by_name = {func.__name__: func for func in funcs}

        def invoke(self, toolname: str, arguments: Dict[str, Any], return_type: Type[T])->T:
            func = self._funcs_by_name.get(toolname)
            assert callable(func), f"Tool {toolname} was not found"
            return func(**arguments)

    run_calculator(gen_result, DummyInvoker(), True)
