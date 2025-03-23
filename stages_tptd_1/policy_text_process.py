import argparse
import json
import os
from typing import Dict, List, Any, Optional

from langgraph.graph import StateGraph
from matplotlib import pyplot as plt

from azure_wrapper import AzureWrepper

llm = AzureWrepper()


class TPTDState(Dict[str, Any]):
    policy_text: str
    tools: List[str]
    target_tool: str
    target_tool_description: Dict
    TPTD: Optional[Dict]
    review_comments: Optional[str]
    review_score: Optional[int]
    iteration: int
    next_step: str
    outdir: str


def read_prompt_file(filename: str) -> str:
    with open(os.path.join(os.path.dirname(__file__), "prompts", filename), "r") as f:
        return f.read()


def generate_messages(system_prompt: str, user_content: str) -> List[Dict[str, str]]:
    return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]


def save_output(outdir: str, filename: str, content: Any):
    with open(os.path.join(outdir, filename), "w") as outfile:
        json.dump(content, outfile, indent=4)


def reviewer_should_stop(state: TPTDState) -> bool:
	if state.get("review_score", {}).get("score", 0) == 5:
		state.update({"iteration": 0})
		return True
	return False


def fixer_should_stop(state: TPTDState) -> bool:
	if state["iteration"]>=3:
		state.update({"iteration": 0})
		return True
	return False
	


class Phase2:
	def __init__(self):
		workflow = StateGraph(TPTDState)
		workflow.add_node("policy_creator", self.policy_creator_node)
		workflow.add_node("coverage_reviewer", self.policy_coverage_review)
		workflow.add_node("coverage_fixer", self.coverage_fixer_node)
		workflow.add_node("standalone_reviewer", self.policy_standalone_review)
		workflow.add_node("standalone_fixer", self.standalone_fixer_node)
		workflow.add_node("examples_creator", self.examples_creator)
		workflow.add_node("examples_reviewer", self.policy_examples_review)
		workflow.add_node("examples_fixer", self.examples_fixer_node)
		workflow.add_node("final", lambda state: state)
		
		workflow.set_entry_point("policy_creator")
		workflow.add_edge("policy_creator", "coverage_reviewer")
		workflow.add_conditional_edges("coverage_reviewer", lambda state: "standalone_reviewer" if reviewer_should_stop(state) else "coverage_fixer")
		workflow.add_conditional_edges("coverage_fixer", lambda state: "standalone_reviewer" if fixer_should_stop(state) else "coverage_reviewer")
		workflow.add_conditional_edges("standalone_reviewer", lambda state: "examples_creator" if reviewer_should_stop(state) else "standalone_fixer")
		workflow.add_conditional_edges("standalone_fixer", lambda state: "examples_creator" if fixer_should_stop(state) else "standalone_reviewer")
		workflow.add_edge("examples_creator", "examples_reviewer")
		workflow.add_conditional_edges("examples_reviewer",lambda state: "final" if reviewer_should_stop(state) else "examples_fixer")
		workflow.add_conditional_edges("examples_fixer", lambda state: "final" if fixer_should_stop(state) else "examples_reviewer")
		
		self.executor = workflow.compile()
	
		
		
		
	def policy_creator_node(self, state: TPTDState) -> TPTDState:
		system_prompt = read_prompt_file("create_policy")
		system_prompt = system_prompt.replace("ToolX",state["target_tool"])
		user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}"
		response = llm.chat_json(generate_messages(system_prompt, user_content))
		state.update({"TPTD": response, "iteration": 0})
		save_output(state["outdir"], f"{state['target_tool']}_0.json", response)
		return state

	def policy_coverage_review(self, state: TPTDState) -> TPTDState:
		system_prompt = read_prompt_file("coverage_reviewer")
		user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nTPTD: {json.dumps(state['TPTD'])}"
		response = llm.chat_json(generate_messages(system_prompt, user_content))
		state.update({"review_score": response["global_score"], "review_comments": response["review"], "iteration": state["iteration"] + 1})
		save_output(state["outdir"], f"{state['target_tool']}_review_coverage_{state['iteration']}.json", response)
		return state

	def coverage_fixer_node(self, state: TPTDState) -> TPTDState:
		system_prompt = read_prompt_file("coverage_fixer")
		user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nTPTD: {json.dumps(state['TPTD'])}\nReview Comments: {json.dumps(state['review_comments'])}"
		response = llm.chat_json(generate_messages(system_prompt, user_content))
		state.update({"TPTD": response})
		save_output(state["outdir"], f"{state['target_tool']}_fix_coverage_{state['iteration']}.json", response)
		return state

	def policy_standalone_review(self, state: TPTDState) -> TPTDState:
		system_prompt = read_prompt_file("standalone_reviewer")
		user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nTPTD: {json.dumps(state['TPTD'])}"
		response = llm.chat_json(generate_messages(system_prompt, user_content))
		state.update({"review_score": response["global_score"], "review_comments": response["review"], "iteration": state["iteration"] + 1})
		save_output(state["outdir"], f"{state['target_tool']}_review_standalone_{state['iteration']}.json", response)
		return state

	def standalone_fixer_node(self, state: TPTDState) -> TPTDState:
		system_prompt = read_prompt_file("standalone_fixer")
		user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nTPTD: {json.dumps(state['TPTD'])}\nReview Comments: {json.dumps(state['review_comments'])}"
		response = llm.chat_json(generate_messages(system_prompt, user_content))
		state.update({"TPTD": response})
		save_output(state["outdir"], f"{state['target_tool']}_fix_standalone_{state['iteration']}.json", response)
		return state
	
	def examples_creator(self, state: TPTDState) -> TPTDState:
		system_prompt = read_prompt_file("create_examples")
		user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}"
		response = llm.chat_json(generate_messages(system_prompt, user_content))
		state.update({"TPTD": response, "iteration": 0})
		save_output(state["outdir"], f"{state['target_tool']}_examples_0.json", response)
		return state
	
	def policy_examples_review(self, state: TPTDState) -> TPTDState:
		system_prompt = read_prompt_file("examples_reviewer")
		user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nTPTD: {json.dumps(state['TPTD'])}"
		response = llm.chat_json(generate_messages(system_prompt, user_content))
		state.update({"review_score": response["global_score"], "review_comments": response["review"], "iteration": state["iteration"] + 1})
		save_output(state["outdir"], f"{state['target_tool']}_review_examples_{state['iteration']}.json", response)
		return state

	def examples_fixer_node(self, state: TPTDState) -> TPTDState:
		system_prompt = read_prompt_file("examples_fixer")
		user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nTPTD: {json.dumps(state['TPTD'])}\nReview Comments: {json.dumps(state['review_comments'])}"
		response = llm.chat_json(generate_messages(system_prompt, user_content))
		state.update({"TPTD": response})
		save_output(state["outdir"], f"{state['target_tool']}_fix_examples_{state['iteration']}.json", response)
		return state





if __name__ == '__main__':
	
	parser = argparse.ArgumentParser(description='parser')
	parser.add_argument('--model-type', type=str,default='ASURE')
	parser.add_argument('--model-name', type=str,default='gpt-4o-2024-08-06')
	parser.add_argument('--policy-path', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/wiki.md')
	parser.add_argument('--outdir', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/process')
	#parser.add_argument('--functions-schema', type=str, default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/airline.json')
	parser.add_argument('--functions-schema', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/fc_schema.json')
	args = parser.parse_args()
	policy_path = args.policy_path
	outdir = args.outdir
	model_type = args.model_type
	model_name = args.model_name
	functions_schema = args.functions_schema

	policy_text = open(policy_path, 'r',encoding='utf-8').read()
	with open(functions_schema, 'r') as file:
		functions =  json.load(file)
	
	fsummary = {}
	for k, v in functions.items():
		fsummary[k] = v['description']
	
	for function_name, function_data in functions.items():
		fname = function_data["name"]
		input_state = {
						"policy_text": policy_text,
						"tools": fsummary,
						"target_tool": fname,
						"target_tool_description": function_data,
						"outdir":outdir
						}
						
	

	
	# if 'paths' in functions:
	# 	for path, methods in functions["paths"].items():
	# 		for method, details in methods.items():
	# 			if isinstance(details, dict) and "operationId" in details:
	# 				operation_id = details["operationId"]
	# 				description = details.get("description", "No description available.")
	# 				fsummary[operation_id] = description
	#
	# 	for path, methods in functions["paths"].items():
	# 		for method, details in methods.items():
	# 			if isinstance(details, dict) and "operationId" in details:
	# 				fname = details["operationId"]
	# 				input_state = {
	# 					"policy_text": policy_text,
	# 					"tools": fsummary,
	# 					"target_tool": fname,
	# 					"target_tool_description": {path:methods},
	# 					"outdir":outdir
	# 				}
	# 				break
					
		p2 = Phase2()
		final_output = p2.executor.invoke(input_state)
		print(json.dumps(final_output))
		tmpoutdir = "/Users/naamazwerdling/Documents/OASB/policy_validation/airline/final"
		outcontent = final_output["TPTD"]
		
		#out = json.loads(outcontent)
		with open(os.path.join(tmpoutdir, fname +  ".json"), "w") as outfile:
			outfile.write(json.dumps(outcontent))
