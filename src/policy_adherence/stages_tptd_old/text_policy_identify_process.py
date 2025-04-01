import argparse
import json
import os
import markdown
from langgraph.graph import StateGraph

from policy_adherence.llm.azure_wrapper import AzureLitellm
from policy_adherence.stages_tptd.utils import reviewer_should_stop, fixer_should_stop, read_prompt_file, \
	generate_messages, save_output, \
	TPTDState, find_mismatched_references, route_by_status, ref_fixer_should_stop

model = 'gpt-4o-2024-08-06'
llm = AzureLitellm(model)

class PolicyIdentifier:
	def __init__(self):
		workflow = StateGraph(TPTDState)
		workflow.add_node("policy_creator", self.policy_creator_node)
		workflow.add_node("reference_correctness", self.reference_correctness)
		workflow.add_node("reference_fixer", self.reference_correctness_fixer_node)
		workflow.add_node("coverage_reviewer", self.policy_coverage_review)
		workflow.add_node("coverage_fixer", self.coverage_fixer_node)
		#workflow.add_node("final", lambda state: state)
		workflow.add_node("final", lambda state: state)
		
		# Option 1:
		# workflow.set_entry_point("policy_creator")
		# workflow.add_edge("policy_creator", "reference_correctness")
		# workflow.add_conditional_edges("reference_correctness", lambda state: route_by_status(state))
		# workflow.add_conditional_edges("reference_fixer",lambda state: "final" if state.get("stop",False) else "coverage_reviewer")
		# workflow.add_conditional_edges("coverage_reviewer", lambda state: "reference_correctness" if state.get("stop",False) else "coverage_fixer")
		# workflow.add_conditional_edges("coverage_fixer", lambda state: "reference_correctness" if state.get("stop",False) else "coverage_reviewer")
		
		
		#option 2:
		# workflow.set_entry_point("policy_creator")
		# workflow.add_edge("policy_creator", "coverage_reviewer")
		# workflow.add_conditional_edges("coverage_reviewer", lambda state: "reference_correctness" if state.get("stop", False) else "coverage_fixer" )
		# workflow.add_conditional_edges("coverage_fixer", lambda state: "reference_correctness" if state.get("stop",False) else "coverage_reviewer")
		# workflow.add_conditional_edges("reference_correctness", lambda state: route_by_status(state))
		# workflow.add_edge("reference_fixer","reference_correctness")
		
		#option 3:
		# workflow.set_entry_point("policy_creator")
		# workflow.add_edge("policy_creator", "coverage_reviewer")
		# workflow.add_conditional_edges("coverage_reviewer", lambda state: "final" if state.get("stop",False) else "coverage_fixer")
		# workflow.add_conditional_edges("coverage_fixer", lambda state: "final" if state.get("stop",False) else "coverage_reviewer")
		
		# option 4:
		workflow.set_entry_point("policy_creator")
		workflow.add_edge("policy_creator", "coverage_reviewer")
		workflow.add_conditional_edges("coverage_reviewer", lambda state: "reference_correctness" if state.get("stop", False) else "coverage_fixer" )
		workflow.add_conditional_edges("coverage_fixer", lambda state: "reference_correctness" if state.get("stop",False) else "coverage_reviewer")
		workflow.add_edge("reference_correctness", "reference_fixer")
		workflow.add_edge("reference_fixer","final")
		
		self.executor = workflow.compile()
		
		
		
		
	def policy_creator_node(self, state: TPTDState) -> TPTDState:
		print("policy_creator_node")
		system_prompt = read_prompt_file("create_policy")
		system_prompt = system_prompt.replace("ToolX",state["target_tool"])
		print(json.dumps(state['target_tool_description']))
		user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}"
		response = llm.chat_json(generate_messages(system_prompt, user_content))
		state.update({"TPTD": response, "iteration": 0})
		save_output(state["outdir"], f"{state['target_tool']}_0.json", response)
		return state
	
	def reference_correctness(self, state: TPTDState) -> TPTDState:
		print("reference_correctness")
		policy_text = state["policy_text"]
		tptd = state["TPTD"]
		corrections, unmatched_policies = find_mismatched_references(policy_text,tptd)
		state["TPTD"] = corrections
		state["reference_mismatch"] = unmatched_policies
		state["iteration"] =  state["iteration"] + 1
		save_output(state["outdir"], f"{state['target_tool']}_ref_{state['iteration']}.json", unmatched_policies)
		return state
	
	def reference_correctness_fixer_node(self, state: TPTDState) -> TPTDState:
		print("reference_correctness_fixer_node")
		if len(state.get("reference_mismatch", {})) > 0:
			system_prompt = read_prompt_file("ref_fixer")
			user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nTPTD: {json.dumps(state['TPTD'])}\npolicies with wrong reference: {json.dumps(state['reference_mismatch'])}"
			response = llm.chat_json(generate_messages(system_prompt, user_content))
			state.update({"TPTD": response})
			save_output(state["outdir"], f"{state['target_tool']}_ref_fixer_{state['iteration']}.json", response)
			return state
		else:
			return state

	def policy_coverage_review(self, state: TPTDState) -> TPTDState:
		print("policy_coverage_review")
		system_prompt = read_prompt_file("coverage_reviewer")
		user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nTPTD: {json.dumps(state['TPTD'])}"
		response = llm.chat_json(generate_messages(system_prompt, user_content))
		state.update({"review_score": response["global_score"], "review_comments": response["review"]})
		if response["global_score"]["score"]==5:
			state.update({"stop":True})
		state["iteration"] = state["iteration"] + 1
		save_output(state["outdir"], f"{state['target_tool']}_review_coverage_{state['iteration']}.json", response)
		return state

	def coverage_fixer_node(self, state: TPTDState) -> TPTDState:
		print("coverage_fixer_node")
		system_prompt = read_prompt_file("coverage_fixer")
		user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nTPTD: {json.dumps(state['TPTD'])}\nReview Comments: {json.dumps(state['review_comments'])}"
		response = llm.chat_json(generate_messages(system_prompt, user_content))
		state.update({"TPTD": response})
		if state["iteration"]> 3:
			state.update({"stop":True})
		save_output(state["outdir"], f"{state['target_tool']}_fix_coverage_{state['iteration']}.json", response)
		return state

	

if __name__ == '__main__':
	
	parser = argparse.ArgumentParser(description='parser')
	parser.add_argument('--model-type', type=str,default='ASURE')
	parser.add_argument('--model-name', type=str,default='gpt-4o-2024-08-06')
	parser.add_argument('--policy-path', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/wiki.md')
	parser.add_argument('--outdir', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline')
	#parser.add_argument('--functions-schema', type=str, default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/airline.json')
	parser.add_argument('--functions-schema', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/fc_schema.json')
	args = parser.parse_args()
	policy_path = args.policy_path
	outdir = args.outdir
	model_type = args.model_type
	model_name = args.model_name
	functions_schema = args.functions_schema

	policy_text = open(policy_path, 'r',encoding='utf-8').read()
	print(policy_text)
	policy_text = markdown.markdown(policy_text)
	print(policy_text)
	with open(functions_schema, 'r') as file:
		functions = json.load(file)
	
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
						"outdir":os.path.join(outdir,"process")
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
	# 		# if path != "/reservations":
	# 		# 	print(path)
	# 		# 	continue
	# 		for method, details in methods.items():
	# 			if isinstance(details, dict) and "operationId" in details:
	# 				fname = details["operationId"]
	# 				input_state = {
	# 					"policy_text": policy_text,
	# 					"tools": fsummary,
	# 					"target_tool": fname,
	# 					"target_tool_description": {path:methods},
	# 					"outdir":os.path.join(outdir,"process")
	# 				}
	# 				break
					
		p2 = PolicyIdentifier()
		final_output = p2.executor.invoke(input_state)
		print(json.dumps(final_output))
		tmpoutdir = os.path.join(outdir,"final")
		outcontent = final_output["TPTD"]
		
		#out = json.loads(outcontent)
		with open(os.path.join(tmpoutdir, fname +  ".json"), "w") as outfile:
			outfile.write(json.dumps(outcontent))
