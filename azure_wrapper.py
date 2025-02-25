import json
import os
from typing import List, Dict

import openai

class AzureWrepper():
	def __init__(self,):
		openai.api_type = "azure"
		openai.api_base = os.getenv("AZURE_API_BASE")
		openai.api_key = os.getenv("AZURE_OPENAI_KEY")
		openai.api_version = os.getenv("AZURE_API_VERSION")
	
	def generate(self,query:str,instruct:str=None,model:str="gpt-4o-2024-08-06",temperature=0.7):
		messages = []
		if instruct:
			messages.append({"role":"system","content":instruct})
		messages.append({"role": "user", "content": query})
		response = openai.ChatCompletion.create(
			engine=model,
			messages=messages,
			temperature=temperature
		)
		res = response["choices"][0]["message"]["content"]
		return res
	
	def chat(self,messages:List[Dict],model:str="gpt-4o-2024-08-06",temperature=0.7):
		response = openai.ChatCompletion.create(
			engine=model,
			messages=messages,
			temperature=temperature,

		)
		res = response["choices"][0]["message"]["content"]
		return res
	
	def chat_json(self,messages:List[Dict],model:str="gpt-4o-2024-08-06",temperature=0.7):
		response = openai.ChatCompletion.create(engine=model,messages=messages,temperature=temperature,response_format={"type": "json_object"})
		res = response["choices"][0]["message"]["content"]
		return json.loads(res)
		
	
	
if __name__ == '__main__':
	aw = AzureWrepper()
	resp = aw.chat([{"role":"user","content":"what is the wheather?"}])
	print(resp)
	resp = aw.generate("how are you today")
	print(resp)
	resp = aw.generate("how are you today","please answer in json format")
	print(resp)