import json
import os

from policy_adherence.llm.azure_wrapper import AzureLitellm
from policy_adherence.stages_tptd.utils import read_prompt_file, generate_messages




class CreateOAS:
	def __init__(self,tools_dir,out_file):
		self.tools_dir = tools_dir
		self.out_file = out_file
		model = 'gpt-4o-2024-08-06'
		self.llm = AzureLitellm(model)
	
		operations = {}
		with open(os.path.join(os.path.dirname(__file__), "prompt"), "r") as f:
			system_prompt = f.read()
		with open(os.path.join(os.path.dirname(__file__), "records"), "r") as f:
			records = f.read()
		for filename in os.listdir(tools_dir):
			if filename.endswith(".py") and not (filename.startswith("__")):
				name = filename.split(".py")[0]
				with open(os.path.join(self.tools_dir, filename), "r") as f:
					function_code = f.read()
				user_content = "Records: "+records +"\n"+"Code: "+function_code
				response = self.llm.chat_json(generate_messages(system_prompt, user_content))
				operations[name] = response
				
		#TODO: CREATE ONE OAS
		with open(out_file, "w") as outfile:
			json.dump(operations, outfile, indent=4)
		
	








code_dir = "/Users/naamazwerdling/workspace/tau-bench/tau_bench/envs/airline/tools"
outfile = "/Users/naamazwerdling/Documents/OASB/policy_validation/airline/operations.json"
CreateOAS(code_dir,outfile)