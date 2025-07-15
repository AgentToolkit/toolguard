import argparse
import asyncio
import os
from os.path import join
import sys
from typing import Dict, List, Optional

import markdown
import json
import yaml
from pathlib import Path
from loguru import logger

#important to load the env variables BEFORE policy_adherence library (so programmatic_ai configuration will take place)
import dotenv

from toolguard.llm.tg_litellm import LitellmModel
from toolguard.llm.tg_llm import TG_LLM
from toolguard.runtime import ToolGuardsCodeGenerationResult
from toolguard.stages_tptd.create_oas_summary import OASSummarizer

dotenv.load_dotenv()


from toolguard.data_types import ToolPolicy, ToolPolicyItem
from toolguard.gen_tool_policy_check import generate_tools_check_fns
from toolguard.stages_tptd.text_tool_policy_generator import step1_main, step1_main_with_tools






async def step2(funcs:list[callable], step1_path:str, step2_path:str, tools:Optional[List[str]]=None)->ToolGuardsCodeGenerationResult:
	os.makedirs(step2_path, exist_ok=True)
	files = [f for f in os.listdir(step1_path) 
		  if os.path.isfile(join(step1_path, f)) and f.endswith(".json")]
	
	tool_policies = []
	for file in files:
		tool_name = file[:-len(".json")]
		if (not tools) or (tool_name in tools):
			policy = load_tool_policy(join(step1_path, file), tool_name)

			tool_policies.append(policy)
	
	return await generate_tools_check_fns("my_app", tool_policies, step2_path, funcs=funcs)

def main(policy_text:str,tools, step1_out_dir:str, step2_out_dir:str, step1_llm:TG_LLM, tools2run:List[str]=None,short1=False):
	step1_main_with_tools(policy_text, tools, step1_out_dir,step1_llm, tools2run, short1)
	result = asyncio.run(step2(tools, step1_out_dir, step2_out_dir, tools2run))
	return result

	


def load_tool_policy(file_path:str, tool_name:str)->ToolPolicy:
    with open(file_path, "r") as file:
        d = json.load(file)
    
    items = [ToolPolicyItem(
                name=item.get("policy_name"),
                description = item.get("description"),
                references = item.get("references"),
                compliance_examples = item.get("compliance_examples"),
                violation_examples = item.get("violating_examples")
            )
            for item in d.get("policies", [])
            if not item.get("skip")]
    return ToolPolicy(name=tool_name, policy_items=items)


if __name__ == '__main__':
	logger.remove()
	logger.add(sys.stdout, colorize=True, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> <level>{message}</level>")
	
	parser = argparse.ArgumentParser(description='parser')
	parser.add_argument('--policy-path', type=str, help='Path to the policy file. Currently, in `markdown` syntax. eg: `/Users/me/airline/wiki.md`')
	parser.add_argument('--tools-py-file', type=str, default="/Users/naamazwerdling/workspace/ToolGuardAgent/src/appointment_app/lg_tools.py")
	parser.add_argument('--out-dir', type=str, help='Path to an output folder where the generated artifacts will be written. eg: `/Users/me/airline/outdir2')
	parser.add_argument('--step1-dir-name', type=str, default='Step1', help='Step1 folder name under the output folder')
	parser.add_argument('--step2-dir-name', type=str, default='Step2', help='Step2 folder name under the output folder')
	parser.add_argument('--step1-model-name', type=str, default='gpt-4o-2024-08-06', help='Model to use for generating in step 1')
	parser.add_argument('--tools2run', nargs='+', default=None, help='Optional list of tool names. These are a subset of the tools in the openAPI operation ids.')
	parser.add_argument('--short-step1', action='store_true', default=False, help='run short version of step 1')
	
	args = parser.parse_args()
	policy_path = args.policy_path
	
	policy_text = open(policy_path, 'r', encoding='utf-8').read()
	policy_text = markdown.markdown(policy_text)
	llm = LitellmModel(args.step1_model_name)
	
	tools_py_file = args.tools_py_file
	file_path = args.tools_py_file
	import importlib.util
	import inspect
	module_name = os.path.splitext(os.path.basename(file_path))[0]
	
	# Add project root to sys.path
	project_root = os.path.abspath(os.path.join(file_path, "..", ".."))  # Adjust as needed
	if project_root not in sys.path:
		sys.path.insert(0, project_root)
	
	spec = importlib.util.spec_from_file_location(module_name, file_path)
	if not spec or not spec.loader:
		raise ImportError(f"Could not load module from {file_path}")
	
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	tools = []
	for name, obj in inspect.getmembers(module):
		if callable(obj) and hasattr(obj, 'name') and hasattr(obj, 'args_schema'):
			tools.append(obj)

	
	main(
		policy_text = policy_text, 
		tools = tools,
		step1_out_dir = os.path.join(args.out_dir, args.step1_dir_name), 
		step2_out_dir = os.path.join(args.out_dir, args.step2_dir_name),
		step1_llm = llm,
		tools2run = args.tools2run,
		short1 = args.short_step1
	)
	
