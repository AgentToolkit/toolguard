import dotenv
import json

from middleware_core.llm import ValidatingLLMClient, get_llm


class TG_LLMEval:
	
	def __init__(self, llm_client):
		if not isinstance(llm_client, ValidatingLLMClient):
			print("llm_client is a ValidatingLLMClient")
			exit(1)
		self.llm_client = llm_client
		
	
	def chat_json(self, messages: list[dict],schema=dict) -> dict:
		return self.llm_client.generate(
			prompt=messages,
			schema=schema,
			retries=5,
			schema_field=None
		)
	
	def generate(self, messages: list[dict]) -> str:
		return self.llm_client.generate(
			prompt=messages,
			schema=str,
			retries=5,
			schema_field=None
		)
		


if __name__ == '__main__':

	dotenv.load_dotenv()
	model = "gpt-4o-2024-08-06"
	OPENAILiteLLMClientOutputVal = get_llm("litellm.output_val")
	client = OPENAILiteLLMClientOutputVal(
		model_path="gpt-4o-2024-08-06",
		custom_llm_provider="azure",
	)
	
	aw = TG_LLMEval(client)
	resp = aw.generate([{"role": "user", "content": "please return json of country and capital for England, France and spain"}])
	print(resp)
	resp = aw.chat_json([{"role": "user", "content": "please return json of country and capital for England, France and spain"}])
	print(resp)
	
	
	

	
	
	
	
	
	