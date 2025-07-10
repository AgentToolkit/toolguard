import json
import os

from toolguard.llm.tg_litellm import LitellmModel
from toolguard.stages_tptd.utils import read_prompt_file, generate_messages
import dotenv
dotenv.load_dotenv()



class CreateOAS:
	def __init__(self,tools_dir,out_file,oas_outfile):
		self.tools_dir = tools_dir
		self.out_file = out_file
		model = 'gpt-4o-2024-08-06'
		self.llm = LitellmModel(model)
		oas = {"openapi": "3.0.3",
			   "info": {
				   "title": "Flight Booking API",
				   "version": "1.0.0"
			   },
			   "paths": {}}
		
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
				oas["paths"].update(response["paths"])
		
				

		
		with open(oas_outfile, "w") as outfile:
			json.dump(oas, outfile, indent=4)
		with open(out_file, "w") as outfile:
			json.dump(operations, outfile, indent=4)
		
	








code_dir = "/Users/naamazwerdling/workspace/tau-bench/tau_bench/envs/airline/tools"
outfile = "/Users/naamazwerdling/Documents/OASB/policy_validation/airline/operations3.json"
oas_outfile = "/Users/naamazwerdling/Documents/OASB/policy_validation/airline/oas3.json"
CreateOAS(code_dir,outfile,oas_outfile)