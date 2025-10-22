import asyncio
import os
import shutil
import sys
from typing import List

import markdown
import dotenv
dotenv.load_dotenv()

from toolguard import build_toolguards
from toolguard.llm.tg_litellm import LitellmModel
from toolguard.tool_policy_extractor.text_tool_policy_generator import extract_functions


class ToolGuardFullFlow:
	def __init__(self,wiki_path,work_dir,tools,llm_model:str="gpt-4o-2024-08-06",app_name:str="my_app"):
		self.llm_model = llm_model
		self.wiki_path = wiki_path
		self.app_name = app_name
		self.tools = tools
		self.work_dir = os.path.join(work_dir, llm_model) #todo: add timestemp
		os.makedirs(work_dir, exist_ok=True)
		policy_text = open(wiki_path, 'r', encoding='utf-8').read()
		self.policy_text = markdown.markdown(policy_text)
		self.llm = LitellmModel(llm_model, "azure")
		self.pydir = None
		self.tool_registry = {
			(getattr(tool, "name", None) or getattr(tool, "__name__", None)): tool
			for tool in tools
			if getattr(tool, "name", None) or getattr(tool, "__name__", None)
		}
		
	async def build_toolguards(self,tools2run: List[str] | None=None, short1=True):
		self.pydir = await build_toolguards(self.policy_text,self.tools,self.work_dir, self.llm, self.app_name, tools2run, short1)
		
	def guard_tool_pass(self, tool_name:str,tool_params:dict) -> bool:
		print("validate_tool_node")
		import sys
		sys.path.insert(0, self.pydir)
		from rt_toolguard import load_toolguards
		toolguards = load_toolguards(self.pydir)
		from rt_toolguard.data_types import PolicyViolationException

		try:
			# app_guards.check_tool_call(tool_name, tool_parms, state["messages"])
			toolguards.check_toolcall(tool_name, tool_params, list(self.tool_registry.values()))
			print("ok to invoke tool")
			return True
		except Exception as e:
			error_message = "it is against the policy to invoke tool: " + tool_name + " Error: " + str(e)
			print(error_message)
			return False

	
	
if __name__ == '__main__':
	wiki_path = "examples/calculator/inputs/policy_doc.md"
	work_dir = "examples/calculator/outputs/fullflow"
	#callable
	callable_path = "examples/calculator/inputs/callable_tools.py"
	tools = extract_functions(callable_path)
	shutil.rmtree(work_dir, ignore_errors=True);
	tgb = ToolGuardFullFlow(wiki_path, work_dir, tools, app_name="calculator")
	asyncio.run(tgb.build_toolguards())
	result_fail = tgb.guard_tool_pass("divide_tool", {"g": 5, "h": 0})
	print(result_fail)
	resullt_success = tgb.guard_tool_pass("divide_tool", {"g": 5, "h": 4})
	print(resullt_success)
	
	
	
	
	
