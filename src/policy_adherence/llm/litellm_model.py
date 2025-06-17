import json
import os
import re
from typing import List, Dict
import time
from litellm import completion
from litellm.types.utils import ModelResponse
from litellm.exceptions import RateLimitError
import json
from jsonschema import validate, ValidationError

from src.policy_adherence.llm.llm_model import LLM_model
import dotenv


model_name_to_endpoint_list=[
#	{"endpoint":"https://ete-litellm.bx.cloud9.ibm.com", "model_name":"claude-3-7-sonnet"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/avengers-jamba-9b","model_name":"ibm-fms/avengers-jamba-9b"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/codellama-34b-instruct-hf","model_name":"codellama/CodeLlama-34b-Instruct-hf"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/deepseek-coder-33b-instruct","model_name":"deepseek-ai/DeepSeek-V2.5"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/deepseek-v2-5/v1","model_name":"deepseek-ai/DeepSeek-V2.5"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/deepseek-v3/v1","model_name":"deepseek-ai/DeepSeek-V3"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/gemma-2-9b-it","model_name":"google/gemma-2-9b-it"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-13b-chat-v2","model_name":"ibm-granite/granite-13b-chat-v2"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-13b-instruct-v2","model_name":"ibm-granite/granite-13b-instruct-v2"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-20b-cbcl","model_name":"ibm-granite/granite-20b-code-base-content-linking"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-20b-cbsl","model_name":"ibm/granite-20b-schema-sqlinstruct-granite-fine-vs"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-20b-cbsql","model_name":"ibm-granite/granite-20b-code-base-sql-gen"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-20b-ci-r1-1","model_name":"ibm-granite/granite-20b-code-instruct-r1.1"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-20b-code-8k-ansible","model_name":"ibm/granite-20b-code-8k-ansible"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-20b-code-instruct","model_name":"ibm/granite-20b-code-instruct"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-20b-code-instruct-8k","model_name":"ibm-granite/granite-20b-code-instruct-8k"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-20b-code-instruct-uapi","model_name":"ibm-granite/granite-20b-code-instruct-unified-api"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-20b-functioncalling","model_name":"ibm-granite/granite-20b-functioncalling"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-3-0-8b-instruct","model_name":"ibm-granite/granite-3.0-8b-instruct"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-3-1-8b-content-linking","model_name":"ibm/granite-3-1-8b-content-linking"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-3-1-8b-instruct","model_name":"ibm-granite/granite-3.1-8b-instruct"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-3-1-8b-question-gen","model_name":"ibm/granite-3-1-8b-question-gen"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-3-1-8b-schema-linking","model_name":"ibm/granite-3-1-8b-schema-linking"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-3-1-8b-sql-gen","model_name":"ibm/granite-3-1-8b-sql-gen"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-3-2-8b-instruct","model_name":"ibm-granite/granite-3.2-8b-instruct"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-3-3-8b-instruct/v1/","model_name":"ibm-granite/granite-3.3-8b-instruct"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-34b-code-instruct-8k","model_name":"ibm-granite/granite-34b-code-instruct-8k"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-34b-content-linking","model_name":"ibm/granite-34b-content-linking"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-34b-question-gen","model_name":"ibm/granite-34b-question-gen"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-34b-schema-linking","model_name":"ibm/granite-34b-schema-linking"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-34b-sql-gen","model_name":"ibm/granite-34b-sql-gen"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-7b-lab","model_name":"ibm/granite-7b-lab"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-8b-code-instruct-128k","model_name":"ibm-granite/granite-8b-code-instruct-128k"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-8b-code-instruct-4k","model_name":"ibm-granite/granite-8b-code-instruct-4k"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-8b-instruct-preview-4k","model_name":"ibm-granite/granite-8b-instruct-preview-4k"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-8b-japanese-instruct","model_name":"ibm-granite/granite-8b-japanese-instruct"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/granite-vision-3-2-2b","model_name":"ibm-granite/granite-vision-3.2-2b"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/internvl2-llama3-76b","model_name":"OpenGVLab/InternVL2-Llama3-76B"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/llama-3-1-405b-instruct-fp8","model_name":"meta-llama/llama-3-1-405b-instruct-fp8"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/llama-3-1-70b-instruct","model_name":"meta-llama/llama-3-1-70b-instruct"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/llama-3-1-8b-instruct","model_name":"meta-llama/Llama-3.1-8B-Instruct"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/llama-3-1-test","model_name":"meta-llama/llama-3-1-405b-instruct-fp8"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/llama-3-2-11b-instruct","model_name":"meta-llama/Llama-3.2-11B-Vision-Instruct"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/llama-3-2-90b-instruct","model_name":"meta-llama/Llama-3.2-90B-Vision-Instruct"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/llama-3-3-70b-instruct/v1","model_name":"meta-llama/llama-3-3-70b-instruct"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/microsoft-phi-4/v1","model_name":"microsoft/phi-4"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/mistralai-pixtral-12b-2409","model_name":"mistralai/pixtral-12b-2409"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/mixtral-8x22b-instruct-v01/v1","model_name":"mistralai/mixtral-8x22B-instruct-v0.1"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/mixtral-8x7b-instruct-v01/v1","model_name":"mistralai/mixtral-8x7B-instruct-v0.1"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/mixtral-8x7b-instruct-v01-test","model_name":"mistralai/mixtral-8x7B-instruct-v0.1-test"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/pixtral-large-instruct-2411","model_name":"mistralai/Pixtral-Large-Instruct-2411"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/qwen2-5-72b-instruct/v1","model_name":"Qwen/Qwen2.5-72B-Instruct"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/qwen2-vl-72b-instruct","model_name":"Qwen/Qwen2-VL-72B-Instruct"},
	{"endpoint":"https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com/slate-125m-english-rtrvr-v2","model_name":"ibm/slate-125m-english-rtrvr-v2"}]

model_to_endpoint = {
    entry["model_name"]: entry["endpoint"]
    for entry in model_name_to_endpoint_list
}

anthropic_models = ['claude-3-5-sonnet-latest', 'claude-3-5-haiku']


class LitellmModel(LLM_model):
	def __init__(self,model_name):
		super().__init__(model_name)
		self.rits = False
		self.anthropic = False
		if self.model_name in model_to_endpoint:
			self.rits = True
		if self.model_name in anthropic_models:
			self.anthropic = True
		

	def generate(self, messages: List[Dict])->ModelResponse:
		if self.rits:
			response = completion(
				messages=messages,
				model=self.model_name,
				custom_llm_provider="openai",
				base_url=model_to_endpoint[self.model_name],
				extra_headers={
					'RITS_API_KEY': os.getenv("RITS_API_KEY")
				},
			)
			return response.choices[0].message.content

		else:
			llm_provider = "anthropic" if self.anthropic else "azure"
			response = completion(
				messages=messages,
				model=self.model_name,
				custom_llm_provider=llm_provider)

		# the same format for OpenAI and Anthropic
		return response["choices"][0]["message"]["content"]
	
	def valid_json_gen(self,messages: List[Dict],schema:Dict):
		for attempt in range(5):
			try:
				response = self.chat_json(messages)
				validate(instance=response, schema=schema)
				return response
			except ValidationError as e:
				print(f"Attempt {attempt + 1} failed schema validation: {e.message}")
				# messages.append({
				# 	"role": "system",
				# 	"content": f"Your previous response did not match the schema. Please ensure the response follows this schema strictly: {json.dumps(schema)}"
				# })
			except Exception as e:
				print(f"Attempt {attempt + 1} failed due to error: {str(e)}")
		
		raise ValueError("Failed to get a valid response after 5 attempts.")
	
	
	def chat_json(self, messages: List[Dict], max_retries: int = 5, backoff_factor: float = 1.5) -> Dict:
		retries = 0
		while retries < max_retries:
			try:
				if self.rits:
					response = completion(
						messages=messages,
						model=self.model_name,
						custom_llm_provider="openai",
						base_url=model_to_endpoint[self.model_name],
						extra_headers={
							'RITS_API_KEY': os.getenv("RITS_API_KEY"),
							'Content-Type': 'application/json',
						},
					)
					res = response["choices"][0]["message"]["content"]
					res = self.extract_json_from_string(res)
					if res is None:
						wait_time = backoff_factor ** retries
						print(f"Error: not json format. Retrying in {wait_time:.1f} seconds... (attempt {retries + 1}/{max_retries})")
						print(f"Error: not json format. Retrying in {wait_time:.1f} seconds... (attempt {retries + 1}/{max_retries})")
						print(response["choices"][0]["message"]["content"])
						time.sleep(wait_time)
						retries += 1
					else:
						return res
				else:
					llm_provider = "anthropic" if self.anthropic else "azure"
					response = completion(
						messages=messages,
						model=self.model_name,
						response_format={"type": "json_object"},
						custom_llm_provider=llm_provider
					)
					res = response["choices"][0]["message"]["content"]
					return json.loads(res)
			except RateLimitError as e:
				wait_time = backoff_factor ** retries
				print(f"Rate limit hit. Retrying in {wait_time:.1f} seconds... (attempt {retries + 1}/{max_retries})")
				time.sleep(wait_time)
				retries += 1
			except Exception as e:
				raise RuntimeError(f"Unexpected error during chat completion: {e}")
		raise RuntimeError("Exceeded maximum retries due to rate limits.")
	
	def extract_json_from_string(self,s):
		# Use regex to extract the JSON part from the string
		match = re.search(r'```json\s*(\{.*?\})\s*```', s, re.DOTALL)
		if match:
			json_str = match.group(1)
			try:
				return json.loads(json_str)
			except json.JSONDecodeError as e:
				print(f"Failed to decode JSON: {e}")
				return None
		else:
			## for rits?
			match = re.search(r'(\{[\s\S]*\})', s)
			if match:
				json_str = match.group(1)
				try:
					return json.loads(json_str)
				except json.JSONDecodeError as e:
					print("response:")
					print(s)
					print("match:")
					print(match.group(1))
					print("Failed to parse JSON:", e)
					return None
			
			print("No JSON found in the string.")
			print(s)
			return None
		
		
		
	
	
if __name__ == '__main__':
	dotenv.load_dotenv()
	#model = "gpt-4o-2024-08-06"
	model = "claude-3-5-sonnet-20240620"
	#model = "meta-llama/llama-3-3-70b-instruct"
	aw = LitellmModel(model)
	resp = aw.generate([{"role": "user", "content": "what is the weather?"}])
	print(resp)
	resp = aw.chat_json([{"role": "user", "content": "what is the weather? please answer in json format"}])
	print(resp)
	
