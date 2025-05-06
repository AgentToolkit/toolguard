import argparse
import asyncio
import os
import sys
from typing import Dict

import markdown
import json
import yaml
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from policy_adherence.common.open_api import OpenAPI
from policy_adherence.stages_tptd.text_policy_identify_process import step1_main
from tests.op_only_oas import op_only_oas


def validate_files_exist(oas, step1_path):
	return True


def run_or_validate_step1(policy_text,oas,step1_path,forct_step1):
	if forct_step1 and validate_files_exist(oas,step1_path):
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
	
	step1_main(policy_text, fsummary, fdetails, step1_path)


async def run_step2(oas:Dict,step1_path,step2_path):
	pass

	# oas_path = "/Users/davidboaz/Documents/GitHub/tau_airline/input/openapi.yaml"
	# tool_policy_paths = {
	# 	# "cancel_reservation": "/Users/davidboaz/Documents/GitHub/tau_airline/input/CancelReservation.json",
	# 	"book_reservation": "/Users/davidboaz/Documents/GitHub/tau_airline/input/BookReservation.json"
	# }
	# output_dir = step2_path
	# now = datetime.now()
	# out_folder = os.path.join(output_dir, now.strftime("%Y-%m-%d_%H_%M_%S"))
	# os.makedirs(out_folder, exist_ok=True)
	#
	# tool_policies = [load_tool_policy(tool_policy_path, tool_name)
	# 				 for tool_name, tool_policy_path
	# 				 in tool_policy_paths.items()]
	#
	# result = await generate_tools_check_fns("my_app", tool_policies, out_folder, oas_path)
	#
	# print(f"Domain: {result.domain_file}")
	# for tool_name, tool in result.tools.items():
	# 	print(f"\t{tool_name}\t{tool.tool_check_file.file_name}")
	# 	for test in tool.test_files:
	# 		print(f"\t{test.file_name}")
	


def main(policy_text:str,oas,step1_path,step2_path,forct_step1):
	run_or_validate_step1(policy_text,oas,step1_path,forct_step1)
	asyncio.run(run_step2(oas,step1_path,step2_path))
	
def read_oas_file(filepath):
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



if __name__ == '__main__':
	load_dotenv()
	logger.remove()
	logger.add(sys.stdout, colorize=True, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> <level>{message}</level>")
	
	parser = argparse.ArgumentParser(description='parser')
	parser.add_argument('--policy-path', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/wiki.md')
	parser.add_argument('--oas', type=str, default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/airline.json')
	parser.add_argument('--out-dir', type=str, default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline')
	parser.add_argument('--force-step1',action='store_true',default=False,help='Force execution of step 1 (default: False)')
	parser.add_argument('--step1-dir-name', type=str, default='Step1')
	parser.add_argument('--step2-dir-name', type=str, default='Step2')

	
	args = parser.parse_args()
	policy_path = args.policy_path
	oas_file = args.oas
	policy_text = open(policy_path, 'r', encoding='utf-8').read()
	policy_text = markdown.markdown(policy_text)
	oas = read_oas_file(oas_file)
	main(policy_text,oas,os.path.join(args.out_dir,args.step1_dir_name),os.path.join(args.out_dir,args.step2_dir_name),args.force_step1)
	

	
	



