import dotenv


class TG_LLMEval:
	
	def __init__(self, model_name, temprature: float = 0.7):
		from llmevalkit.llm import get_llm, OutputValidationError
		self.model_name = model_name
		self.temprature = temprature
		OPENAILiteLLMClientOutputVal = get_llm("litellm.output_val")
		self.client = OPENAILiteLLMClientOutputVal(
			# model_name="ibm-granite/granite-3.1-8b-instruct",
			model_path="gpt-4o-2024-08-06",
			custom_llm_provider="azure",
			# api_key="YOUR_API_KEY",           # optional if set in env
			# model_url="custom-model-url",     # optional
			# api_url="https://api.example.com", # optional
			# hooks=[
			# 	# simple hook that prints events
			# 	lambda event, payload: print(f"[HOOK] {event}: {payload}")
			# ],
		)
	
	def chat_json(self, messages: list[dict],schema=dict) -> dict:
		return self.client.generate(
			prompt=messages,
			schema=schema,
			retries=5,
		)
	
	def generate(self, messages: list[dict]) -> str:
		return self.client.generate(
			prompt=messages,
			schema=str,
			retries=5,
		)
		


if __name__ == '__main__':

	dotenv.load_dotenv()
	model = "gpt-4o-2024-08-06"
	# model = "claude-3-5-sonnet-20240620"
	# model = "meta-llama/llama-3-3-70b-instruct"
	aw = TG_LLMEval(model)
	resp = aw.generate([{"role": "user", "content": "please return json of country and capital for England, France and spain"}])
	print(resp)
	resp = aw.chat_json([{"role": "user", "content": "please return json of country and capital for England, France and spain"}])
	print(resp)
	
	# 2.3 JSON Schema dict for a weather object
	weather_schema: dict[str, any] = {
		"type": "object",
		"properties": {
			"city": {"type": "string"},
			"temperature_c": {"type": "number"},
			"condition": {"type": "string"},
		},
		"required": ["city", "temperature_c", "condition"],
		"additionalProperties": False,
	}
	
	

	
	
	
	
	
	