
import asyncio
import inspect
import os
from os.path import join
from typing import Callable, List

import markdown
import logging

from .buildtime import generate_guard_specs, generate_guards_from_specs
from .common import py
from .llm.tg_litellm import LitellmModel

logger = logging.getLogger(__name__)

import argparse

def main():
	parser = argparse.ArgumentParser(description='parser')
	parser.add_argument('--policy-path', type=str, help='Path to the policy file. Currently, in `markdown` syntax. eg: `/Users/me/airline/wiki.md`')
	parser.add_argument('--app-root', type=str, default="../ToolGuardAgent/src/appointment_app")
	parser.add_argument('--app-tools-py-file', type=str, default="lg_tools.py")
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

	llm = LitellmModel(args.step1_model_name, "azure") #FIXME from args
	tools = load_functions_in_file(args.app_root, args.app_tools_py_file)
	os.makedirs(args.out_dir, exist_ok=True)
	step1_out_dir = join(args.out_dir, args.step1_dir_name)
	step2_out_dir = join(args.out_dir, args.step2_dir_name)

	async def build_toolguards():
		specs = await generate_guard_specs(
			policy_text = policy_text, 
			tools = tools, 
			work_dir = step1_out_dir, 
			llm = llm,
			short=args.short_step1,
		)
		guards = await generate_guards_from_specs(
			tool_specs = specs,
			tools = tools, 
			work_dir = step2_out_dir, 
			llm = llm,
			tool_names=args.tools2run
		)
		return guards
		
	asyncio.run(
		build_toolguards()
	)

from importlib import import_module
def load_functions_in_file(py_root:str, file_path: str) -> List[Callable]:
	with py.temp_python_path(py_root):
		module = import_module(py.path_to_module(file_path))
	funcs = []
	for name, obj in inspect.getmembers(module):
		# if isinstance(obj, BaseTool):
		# 	funcs.append(py.unwrap_fn(obj))
		if callable(obj) and not (name=='tool' and obj.__module__ =='langchain_core.tools.convert'):
			funcs.append(obj)
	return funcs