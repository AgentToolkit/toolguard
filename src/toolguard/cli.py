
import asyncio
import os
from os.path import join

import markdown
import logging

from toolguard.buildtime import build_toolguards, load_functions_in_file
from toolguard.llm.tg_litellm import LitellmModel

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
	asyncio.run(
		build_toolguards(
			policy_text = policy_text, 
			tools = tools,
			step1_out_dir = step1_out_dir,
			step2_out_dir = step2_out_dir,
			step1_llm = llm,
			tools2run = args.tools2run,
			short1 = args.short_step1
		)
	)



