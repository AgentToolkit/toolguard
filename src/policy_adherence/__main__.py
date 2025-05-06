import argparse
import asyncio
import os
from os.path import join
import sys
from typing import Dict, List

import markdown
import json
import yaml
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from policy_adherence.common.open_api import OpenAPI
from policy_adherence.data_types import ToolPolicy, ToolPolicyItem, ToolChecksCodeGenerationResult
from policy_adherence.gen_tool_policy_check import generate_tools_check_fns
from policy_adherence.stages_tptd.text_policy_identify_process import step1_main
from tests.op_only_oas import op_only_oas


def validate_files_exist(oas, step1_path):
	if not os.path.isdir(step1_path):
		return False
	if 'paths' in oas:
		for path, methods in oas["paths"].items():
			for method, details in methods.items():
				if isinstance(details, dict) and "operationId" in details:
					operation_id = details["operationId"]
					fname = os.path.join(step1_path,operation_id +'.json')
					if not os.path.isfile(fname):
						return False
	return True


def run_or_validate_step1(policy_text, oas_file:str, step1_out_dir, forct_step1,tools:List[str]=None):
	oas = read_oas_file(oas_file)
	if forct_step1 and validate_files_exist(oas, step1_out_dir):
		return
	fsummary = {}
	fdetails = {}
	if 'paths' in oas:
		for path, methods in oas["paths"].items():
			for method, details in methods.items():
				if isinstance(details, dict) and "operationId" in details:
					operation_id = details["operationId"]
					description = details.get("description", "No description available.")
					fsummary[operation_id] = description
		
		for path, methods in oas["paths"].items():
			for method, details in methods.items():
				if isinstance(details, dict) and "operationId" in details:
					fname = details["operationId"]
					oas = OpenAPI.model_validate(oas)
					op_oas = op_only_oas(oas, fname)
					print(fname)
					fdetails[fname] = op_oas
	
	step1_main(policy_text, fsummary, fdetails, step1_out_dir,tools)


async def run_step2(oas_path:str, step1_path:str, step2_path:str)->ToolChecksCodeGenerationResult:
	os.makedirs(step2_path, exist_ok=True)
	files = [f for f in os.listdir(step1_path) 
		  if os.path.isfile(join(step1_path, f)) and f.endswith(".json")]
	
	tool_policies = []
	for file in files:
		tool_name = file[:-len(".json")]
		tool_policies.append(load_tool_policy(join(step1_path, file), tool_name))
	
	return await generate_tools_check_fns("my_app", tool_policies, step2_path, oas_path)

def main(policy_text:str, oas_file:str, step1_out_dir:str, step2_out_dir:str, forct_step1:bool, run_step2:bool,tools:List[str]=None):
	run_or_validate_step1(policy_text, oas_file, step1_out_dir, forct_step1,tools)
	if run_step2:
		result = asyncio.run(run_step2(oas_file, step1_out_dir, step2_out_dir))
		print(f"Domain: {result.domain_file}")
		for tool_name, tool in result.tools.items():
			print(f"\t{tool_name}\t{tool.tool_check_file.file_name}")
			for test in tool.test_files:
				print(f"\t{test.file_name}")

	
def read_oas_file(filepath:str)->Dict:
	path = Path(filepath)
	if not path.exists():
		raise FileNotFoundError(f"File not found: {filepath}")
	try:
		with open(path, 'r', encoding='utf-8') as file:
			if path.suffix.lower() == '.json':
				return json.load(file)
			elif path.suffix.lower() in ['.yaml', '.yml']:
				return yaml.safe_load(file)
			else:
				raise ValueError("Unsupported file extension. Use .json, .yaml, or .yml")
	except Exception as e:
		raise ValueError(f"Failed to parse file: {e}")

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
	load_dotenv()
	logger.remove()
	logger.add(sys.stdout, colorize=True, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> <level>{message}</level>")
	
	parser = argparse.ArgumentParser(description='parser')
	parser.add_argument('--policy-path', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/wiki.md')
	parser.add_argument('--oas', type=str, default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/airline.json')
	parser.add_argument('--out-dir', type=str, default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/outdir2')
	parser.add_argument('--run-step1',action='store_true',default=False,help='Force execution of step 1 (default: False)')
	parser.add_argument('--run-step2', action='store_true', default=True,help='Execute step 2 (default: True)')
	parser.add_argument('--step1-dir-name', type=str, default='Step1')
	parser.add_argument('--step2-dir-name', type=str, default='Step2')
	#parser.add_argument('--tools',nargs='+',  default=None,  help='Optional list of tool items')
	parser.add_argument('--tools', nargs='+', default=['search_onestop_flight','send_certificate','transfer_to_human_agents'], help='Optional list of tool items')


	args = parser.parse_args()
	policy_path = args.policy_path
	oas_file = args.oas
	policy_text = open(policy_path, 'r', encoding='utf-8').read()
	policy_text = markdown.markdown(policy_text)

	main(policy_text, oas_file, os.path.join(args.out_dir,args.step1_dir_name), os.path.join(args.out_dir,args.step2_dir_name), args.run_step1,args.run_step2,args.tools)
	
