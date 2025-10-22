import asyncio
import shutil
import unittest

from examples.calculator.end2end import ToolGuardFullFlow
from toolguard.tool_policy_extractor.text_tool_policy_generator import extract_functions


class CalculatorTestLGTools(unittest.TestCase):
    def test_calculator_lg(self):
        wiki_path = "examples/calculator/inputs/policy_doc.md"
        work_dir = "examples/calculator/outputs/lg_tools"
        lg_path = "examples/calculator/inputs/lg_tools.py"
        tools = extract_functions(lg_path)
        shutil.rmtree(work_dir, ignore_errors=True);
        tgb = ToolGuardFullFlow(wiki_path, work_dir, tools, app_name="calculator")
        asyncio.run(tgb.build_toolguards())
        fail = tgb.guard_tool_pass("divide_tool", {"g": 5, "h": 0})
        self.assertEqual(fail, False)
        success = tgb.guard_tool_pass("divide_tool", {"g": 5, "h": 4})
        self.assertEqual(success, True)


if __name__ == '__main__':
	unittest.main()
