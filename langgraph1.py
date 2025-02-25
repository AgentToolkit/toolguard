
import json
import langgraph.graph as lg
import os
import openai


openai.api_type = "azure"
openai.api_base = os.getenv("AZURE_API_BASE")
openai.api_key = os.getenv("AZURE_OPENAI_KEY")
openai.api_version = os.getenv("AZURE_API_VERSION")
deployment_name = "gpt-4o-2024-08-06"

example_output = {"name":"UpdateReservationBaggages",
				  "signature":"UpdateReservationBaggages(data: Dict[str, Any],reservation_id: str, total_baggages: int, nonfree_baggages: int, payment_id: str) -> str",
				  "examples":["UpdateReservationBaggages.invoke(data,\"ZFA04Y\", 2, 1, \"credit_card_001\")","UpdateReservationBaggages.invoke(data,\"RYA707\", 0, 1, \"gift_card_001\")"],
				  "description":"Update the baggage information of a reservation.",
				  "params": {
                        "reservation_id": {
                            "type": "string",
                            "description": "The reservation ID, such as 'ZFA04Y'.",
							"required": True
                        },
                        "total_baggages": {
                            "type": "integer",
                            "description": "The updated total number of baggage items included in the reservation.",
							"required": True
                        },
                        "nonfree_baggages": {
                            "type": "integer",
                            "description": "The updated number of non-free baggage items included in the reservation.",
							"required": True
                        },
                        "payment_id": {
                            "type": "string",
                            "description": "The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'.",
							"required": True
                        }
				  }
				  }








# Node 1: Process function call files
class FunctionSummaryNode:
	def __call__(self, input: str) -> dict:
		functions_data = {}
		directory = input['directory']
		for filename in os.listdir(directory):
			if filename.endswith(".py"):
				with open(os.path.join(directory, filename), "r") as f:
					content = f.read()
				messages = [
							   {"role": "system",
								"content": "Extract from the following text the function signature, description of the function and its parameters, and generate 2-3 function call example as diverse and you can with a parameters. output in a json format. for example:\n "+json.dumps(example_output)},
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
		return {"functions": functions_data,"policy_text":input["policy_text"],messages:[{"role": "system","content":"please describe all relevant function calls"},{"role": "assistant","content":functions_data}]}


# Node 2: Identify relevant policies
class PolicyValidationNode:
	def __call__(self, inputs: dict) -> dict:
		functions_data = inputs["functions"]
		policy_text = inputs["policy_text"]
		policies_per_function = {}
		for func_name, func_data in functions_data.items():
			response = openai.ChatCompletion.create(
				engine="gpt-4",
				messages=[
					{"role": "system",
					 "content": "Determine which policies are relevant for validation before calling function: "+func_data['name']},
					{"role": "user",
					 "content": f"Function details:{func_data}\nPolicy: {policy_text}"}
				],
				temperature=0.7
			)
			policies_per_function[func_name] = response["choices"][0]["message"]["content"].split("\n")
		return {"functions": functions_data, "policies": policies_per_function}



class ValidationFunctionNode:
	def __call__(self, inputs: dict) -> dict:
		functions_data = inputs["functions"]
		policies_per_function = inputs["policies"]
		validation_functions = {}
		for func_name, func_data in functions_data.items():
			policies = policies_per_function.get(func_name, [])
			response = openai.ChatCompletion.create(
				engine="gpt-4",
				messages=[
					{"role": "system",
					 "content": "Generate a function to validate policy compliance before calling the function."},
					{"role": "user",
					 "content": f"Function: {func_name}\nDescription: {func_data['description']}\nPolicies: {', '.join(policies)}\nGenerate validate_function{func_name}(params: Dict[str, Any], history: List[Dict], data: Dict[str, Any])"}
				],
				temperature=0.7
			)
			validation_functions[func_name] = response["choices"][0]["message"]["content"]
		return {"validation_functions": validation_functions}


# Build the LangGraph
graph = lg.Graph()
graph.add_node("function_summary", FunctionSummaryNode())
graph.add_node("policy_validation", PolicyValidationNode())
graph.add_node("validation_function", ValidationFunctionNode())

graph.set_entry_point("function_summary")
graph.add_edge("function_summary", "policy_validation")
graph.add_edge("policy_validation", "validation_function")

graph = graph.compile()

# Run the pipeline
if __name__ == "__main__":
	dir = "/Users/naamazwerdling/workspace/tau-bench/tau_bench/envs/airline/tools"
	policy_path = "/Users/naamazwerdling/workspace/tau-bench/tau_bench/envs/airline/wiki.md"
	policy_text = open(policy_path, 'r').read()

	result = graph.invoke({"directory": dir, "policy_text": policy_text})
	
	print("\nFunction Summaries:")
	print(json.dumps(result["functions"], indent=2))
	print("\nRelevant Policies:")
	print(json.dumps(result["policies"], indent=2))
	print("\nGenerated Validation Functions:")
	print(json.dumps(result["validation_functions"], indent=2))
