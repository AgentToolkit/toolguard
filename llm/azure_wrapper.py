import json
import os
from typing import List, Dict

import openai

from llm.llm_model import LLM_model


class AzureWrepper(LLM_model):
	def __init__(self,model_name:str="gpt-4o-2024-08-06",temperature:float=0.7):
		self.model_name = model_name
		self.temperature = temperature
		openai.api_type = "azure"
		openai.api_base = os.getenv("AZURE_API_BASE")
		openai.api_key = os.getenv("AZURE_OPENAI_KEY")
		openai.api_version = os.getenv("AZURE_API_VERSION")
	
	
	
	
	
	def chat_json(self,messages:List[Dict]):
		response = openai.ChatCompletion.create(engine=self.model_name,messages=messages,temperature=self.temperature,response_format={"type": "json_object"})
		res = response["choices"][0]["message"]["content"]
		return json.loads(res)
	
	def generate(self, query: str, instruct: str = None):
		messages = []
		if instruct:
			messages.append({"role": "system", "content": instruct})
		messages.append({"role": "user", "content": query})
		response = openai.ChatCompletion.create(
			engine=self.model_name,
			messages=messages,
			temperature=self.temperature
		)
		res = response["choices"][0]["message"]["content"]
		return res
	
	def chat(self, messages: List[Dict]):
		response = openai.ChatCompletion.create(
			engine=self.model_name,
			messages=messages,
			temperature=self.temperature,
		
		)
		res = response["choices"][0]["message"]["content"]
		return res
		
	
	
if __name__ == '__main__':
	model = "gpt-4o-2024-08-06"
	aw = AzureWrepper(model)
	resp = aw.chat_json([{"role":"user","content":"what is the wheather? please answer in json format"}])
	print(resp)
	