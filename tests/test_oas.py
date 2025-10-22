import asyncio
import shutil
import unittest

from examples.calculator.end2end import ToolGuardFullFlow



class CalculatorTestOAS(unittest.TestCase):
    def test_calculator_oas(self):
        wiki_path = "examples/calculator/inputs/policy_doc.md"
        work_dir = "examples/calculator/outputs/oas"
        oas_path = "examples/calculator/inputs/oas.json"
        shutil.rmtree(work_dir, ignore_errors=True);
        tgb = ToolGuardFullFlow(wiki_path, work_dir, oas_path, app_name="calculator")
        asyncio.run(tgb.build_toolguards())
        fail = tgb.guard_tool_pass("divide_tool", {"g": 5, "h": 0})
        self.assertEqual(fail, False)
        success = tgb.guard_tool_pass("divide_tool", {"g": 5, "h": 4})
        self.assertEqual(success, True)


if __name__ == '__main__':
	unittest.main()
