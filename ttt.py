import json
import os

import openai


def chat_with_gpt(user_message, system_instruction):
	openai.api_type = "azure"
	openai.api_base = os.getenv("AZURE_API_BASE")
	openai.api_key = os.getenv("AZURE_OPENAI_KEY")
	openai.api_version = os.getenv("AZURE_API_VERSION")
	deployment_name = "gpt-4o-2024-08-06"
	
	# response = openai.ChatCompletion.create(
	# 	engine=deployment_name,  # Use "engine" instead of "model" for Azure
	# 	messages=[
	# 		{"role": "system", "content": system_instruction},
	# 		{"role": "user", "content": user_message}
	# 	],
	# 	max_tokens=500
	# )
	#
	# print( response["choices"][0]["message"]["content"])
	
	functions_data = {}
	directory =  "/Users/naamazwerdling/workspace/tau-bench/tau_bench/envs/airline/tools"
	for filename in os.listdir(directory):
		if filename.endswith(".py"):
			with open(os.path.join(directory, filename), "r") as f:
				content = f.read()
			messages = [
						   {"role": "system",
							"content": "Extract from the following text the function signature, description of the function and its parameters, and generate 2-3 function call example as diverse and you can with a parameters. output in a json format"},
						   {"role": "user", "content": content}
					   ]
			response = openai.ChatCompletion.create(
				engine=deployment_name,  # Use "engine" instead of "model" for Azure
				messages=messages,
				temperature=0.7
			)
			resp = response["choices"][0]["message"]["content"]
			resp = resp.strip("```json").strip("```").strip()
			functions_data[filename] = json.loads(resp)
	print(json.dumps(functions_data))


if __name__ == "__main__":
	system_instruction = "You are a helpful assistant."
	user_message = "Hello, how are you?"
	response = chat_with_gpt(user_message, system_instruction)
	print(response)