
import asyncio


import markdown
import logging

from toolguard.core import build_toolguards
from toolguard.llm.tg_litellm import LitellmModel
from toolguard.tool_policy_extractor.text_tool_policy_generator import extract_functions

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

	llm = LitellmModel(args.step1_model_name, "azure") #FIXME from args
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



