import json
import os
from typing import List, Dict

from litellm import completion
from litellm.types.utils import ModelResponse
import openai

from src.policy_adherence.llm.llm_model import LLM_model


class AzureLitellm(LLM_model):
	
	def chat(self, messages: List[Dict]):
		return completion(
            messages=messages,
            model=self.model_name,
            custom_llm_provider= "azure")
	
	def chat_json(self, messages: List[Dict]):
		response =  completion(
            messages=messages,
            model=self.model_name,
			response_format={"type": "json_object"},
            custom_llm_provider= "azure")
		res = response["choices"][0]["message"]["content"]
		return json.loads(res)
	
	
	
# class AzureWrepper(LLM_model):
# 	def __init__(self, model_name:str="gpt-4o-2024-08-06", temperature:float=0.7):
# 		self.model_name = model_name
# 		self.temperature = temperature
# 		openai.api_type = "azure"
# 		openai.base_url = os.getenv("AZURE_API_BASE")
# 		openai.api_key = os.getenv("AZURE_OPENAI_KEY")
# 		openai.api_version = os.getenv("AZURE_API_VERSION")
#
#
# 	def chat_json(self,messages:List[Dict]):
# 		response = openai.chat.completions.create(
# 			model=self.model_name,
# 			messages=messages,
# 			temperature=self.temperature,
# 			response_format={"type": "json_object"}
# 		)
# 		res = response["choices"][0]["message"]["content"]
# 		return json.loads(res)
#
# 	def generate(self, query: str, instruct: str = None):
# 		messages = []
# 		if instruct:
# 			messages.append({"role": "system", "content": instruct})
# 		messages.append({"role": "user", "content": query})
# 		response = openai.chat.completions.create(
# 			model=self.model_name,
# 			messages=messages,
# 			temperature=self.temperature
# 		)
# 		res = response["choices"][0]["message"]["content"]
# 		return res
#
# 	def chat(self, messages: List[Dict]):
# 		response = openai.ChatCompletion.create(
# 			engine=self.model_name,
# 			messages=messages,
# 			temperature=self.temperature,
#
# 		)
# 		res = response["choices"][0]["message"]["content"]
# 		return res
#
	
	
if __name__ == '__main__':
	model = "gpt-4o-2024-08-06"
	aw = AzureLitellm(model)
	resp = aw.chat_json([{"role":"user","content":"what is the wheather? please answer in json format"}])
	print(resp)
	