import json
import os

import dotenv

from toolguard.llm.tg_litellm import LitellmModel

dotenv.load_dotenv()
model = "gpt-4o-2024-08-06"
aw = LitellmModel(model)
input_file = "/Users/naamazwerdling/Documents/OASB/policy_validation/orca/orca_tools.json"
output_dir = "/Users/naamazwerdling/Documents/OASB/policy_validation/orca/"
prompt = """
Instructions: Generate OpenAPI paths JSON from the given information below.

Given:
A Json function name, description and parameters.

Write a JSON object for the OpenAPI paths section that defines an endpoint representing the function as a REST API.
Include:
* Path and Method
    * Use GET if it's a read-only function with simple inputs.
    * Use POST if it changes data or uses complex inputs.
    * Name the path based on the function purpose, like /predict, /create-user.
    * If the function only retrieve data and does not change the data in the dataset, add "x-readOnlyOperation: true", else "x-readOnlyOperation: false"
* Parameters or Request Body
    * For GET: define each input as a query parameter (with name, type, required, description).
    * For POST: use a requestBody with a JSON schema describing the input object.
* Responses
    * Always include a 200 response with a JSON schema for the output.
    * Add an example using the sample data.
    * Use proper OpenAPI data types (string, integer, boolean, array, object).
* Descriptions
    * Add short descriptions for the endpoint, inputs, and output fields.
* Input Examples
    * Directly under get/post add "x-input-examples" which is an array of diverse input parameters examples. for example: [CallMyFunc(1,"Canada", 3.5,True),CallMyFunc(-4,"Canada"),CallMyFunc(0,"USA", 55.0,False)]
* Output Examples
    * Directly under get/post add "x-output-examples" which is an array of diverse input parameters examples. for example: ["left","right"]
* operationId
    * Make sure you add operationId which is matched exactly to the name of the function

expected output should start with:
"paths": {...}

"""
with open(input_file, 'r') as file:
    data = json.load(file)
for domain,actions in data.items():
	print(domain)
	oas = {
  "openapi": "3.0.3",
  "info": {
    "title": domain,
    "description": "An API for "+domain,
    "version": "1.0.0"
  },
  "paths": {}
	}
	dir = os.path.join(output_dir,domain)
	if not os.path.isdir(dir):
		os.makedirs(dir)
	if not os.path.isdir(os.path.join(dir,"actions")):
		os.makedirs(os.path.join(dir,"actions"))
	for a in actions:
		aname = a["name"].replace("_","-")
		print(aname)
		resp = aw.chat_json([{"role": "system", "content": prompt},{"role": "user", "content": "function: "+aname+"\ndata: "+json.dumps(a)}])
		with open(os.path.join(output_dir, domain,"actions", aname+".json"), "w") as outfile:
			json.dump(resp, outfile, indent=4)
		if 'paths' in resp:
			for path in resp['paths']:
				oas["paths"][path]=resp['paths'][path]
		else:
			print("error" + json.dumps(resp))
			print(aname)
			print(json.dumps(a))
			
		
	with open(os.path.join(output_dir,domain,"oas.json"), "w") as outfile:
		json.dump(oas, outfile, indent=4)