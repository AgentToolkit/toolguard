import json
import os

from azure_wrapper import AzureWrepper
import re

class FunctionValidatorGenerator:
	def __init__(self,policy_path:str,function_code_dir:str,outdir:str):
		self.azure_wrapper = AzureWrepper()
		self.policy_text = open(policy_path, 'r').read()
		self.fc_dir = function_code_dir
		self.functions = self.extract_function_data(outdir)
		
		fsummary = {}
		for k, v in self.functions.items():
			fsummary[k] = v['description']
		
		for function_name,function_data in self.functions.items():
			fname = function_data["name"]
			messages = self.extract_policies(function_data,fsummary)
			instruct = self.get_validation_function_prompt(fname,function_data["signature"])
			messages.append({"role": "user", "content": instruct})
			res = self.azure_wrapper.chat(messages)
			match = re.search(r"```python(.*?)```", res, re.DOTALL)
			function= match.group(1).strip() if match else ""
			print(function)
			with open(os.path.join(outdir, "validate_"+fname+".py"), "w") as outfile:
				outfile.write(function)
			
	def get_validation_function_prompt(self,fname,fsig):
		fc_valid_prompt_file = os.path.join(os.path.dirname(__file__), "prompts", "fc_validator_prompt")
		with open(fc_valid_prompt_file, "r") as f:
			instructions = f.read()
			instructions = instructions.replace("__FNAME__",fname)
			instructions = instructions.replace("__FSIG__", fsig)
			return instructions
	
	def extract_policies(self,function_data,func_summary):
		name = function_data["name"]
		# todo: relative
		sys_prompt_file = os.path.join(os.path.dirname(__file__), "prompts", "policies_summary")
		with open(sys_prompt_file, "r") as f:
			system_prompt = f.read()
		fmessages = []
		fmessages.append({"role": "system", "content": system_prompt})
		fmessages.append({"role": "user",
						  "content": "Policy Document:" + self.policy_text + "\nTools Descriptions:" + json.dumps(
							  self.functions) + "\nTarget Tool:" + json.dumps(function_data)})
		
		outfile = os.path.join(outdir, name+".txt")
		if os.path.isfile(outfile):
			with open(outfile, 'r') as file:
				relevant_policies = open(outfile, 'r').read()
		else:
			relevant_policies = self.azure_wrapper.chat(fmessages)
			print(relevant_policies)
			with open(outfile, "w") as outfile:
				outfile.write(relevant_policies)
		fmessages.append({"role": "assistant", "content": relevant_policies})
		return fmessages
	
	def extract_function_data(self,outdir):
		outfile = os.path.join(outdir, "fc_schema.json")
		if os.path.isfile(outfile):
			with open(outfile, 'r') as file:
				return json.load(file)

		prompt_file = os.path.join(os.path.dirname(__file__), "prompts", "function_summary")
		functions_data = {}
		for filename in os.listdir(self.fc_dir):
			if filename.endswith(".py") and not(filename.startswith("__")):
				functions_data[filename] = self.generate_description(os.path.join(self.fc_dir, filename),prompt_file)
		print(json.dumps(functions_data))
		with open(outfile, "w") as outfile:
			outfile.write(json.dumps(functions_data))
		
		return functions_data
		
	
	def generate_description(self,fc_path,prompt1_path):
		with open(prompt1_path, "r") as f:
			system_prompt = f.read()
		with open(prompt1_path.replace("function_summary","records"), "r") as f:
			records = f.read()
		system_prompt = system_prompt.replace("__RECORDS__",records)
		with open(fc_path, "r") as f:
			content = f.read()
		messages = [
			{"role": "system",
			 "content": system_prompt},
			{"role": "user", "content": content}
		]
		
		resp = self.azure_wrapper.chat(messages)
		resp = resp.strip("```json").strip("```").strip()
		return json.loads(resp)
	

	
	
	
	
if __name__ == '__main__':
	dir = "/Users/naamazwerdling/workspace/tau-bench/tau_bench/envs/airline/tools"
	data_dir = "/Users/naamazwerdling/workspace/tau-bench/tau_bench/envs/airline/data"
	policy_path = "/Users/naamazwerdling/workspace/tau-bench/tau_bench/envs/airline/wiki.md"
	#outdir = "/Users/naamazwerdling/Documents/OASB/policy_validation/tau_airline_res"
	outdir = "/Users/naamazwerdling/Documents/OASB/policy_validation/tau_airline_res_temp"
	#policy_text = open(policy_path, 'r').read()
	fvg = FunctionValidatorGenerator(policy_path,dir,outdir)
