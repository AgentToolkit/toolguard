import argparse
import asyncio
import os
import sys
from typing import Callable, List

import markdown
import logging

from toolguard.core import build_toolguards
from toolguard.llm.tg_litellm import LitellmModel

logger = logging.getLogger(__name__)

import argparse

def main():
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
	tools = extract_functions(args.tools_py_file)
	asyncio.run(
		build_toolguards(
			policy_text = policy_text, 
			tools = tools,
			out_dir = args.out_dir,
			step1_llm = llm,
			tools2run = args.tools2run,
			short1 = args.short_step1
		)
	)

def extract_functions(file_path:str) ->List[Callable]:
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
	
	return tools

