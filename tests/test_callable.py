import asyncio
import shutil

from examples.calculator.end2end import ToolGuardFullFlow
from toolguard.tool_policy_extractor.text_tool_policy_generator import extract_functions

def test_calculator_callable():
    wiki_path = "examples/calculator/inputs/policy_doc.md"
    work_dir = "examples/calculator/outputs/callable"
    
    # callable
    callable_path = "examples/calculator/inputs/callable_tools.py"
    tools = extract_functions(callable_path)
    shutil.rmtree(work_dir, ignore_errors=True);
    tgb = ToolGuardFullFlow(wiki_path, work_dir, tools, app_name="calculator")
    asyncio.run(tgb.build_toolguards())
    fail = tgb.guard_tool_pass("divide_tool", {"g": 5, "h": 0})
    assert fail is False
    success = tgb.guard_tool_pass("divide_tool", {"g": 5, "h": 4})
    assert success