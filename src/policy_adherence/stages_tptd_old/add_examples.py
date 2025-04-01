import argparse
import json
import os


from langgraph.graph import StateGraph

from policy_adherence.llm.azure_wrapper import AzureLitellm
from policy_adherence.stages_tptd.utils import reviewer_should_stop, fixer_should_stop, read_prompt_file, generate_messages, save_output, \
	TPTDState

model = 'gpt-4o-2024-08-06'
llm = AzureLitellm(model)




class AddExamples:
	def __init__(self):
		workflow = StateGraph(TPTDState)
		workflow.add_node("examples_creator", self.example_creator)
		workflow.add_node("examples_reviewer", self.example_reviewer)
		workflow.add_node("examples_fixer", self.example_fixer)
		workflow.add_node("final", lambda state: state)
		
		workflow.set_entry_point("examples_creator")
		workflow.add_edge("examples_creator", "examples_reviewer")
		workflow.add_conditional_edges("examples_reviewer", lambda state: "final" if reviewer_should_stop(state) else "examples_fixer")
		workflow.add_conditional_edges("examples_fixer", lambda state: "final" if fixer_should_stop(state) else "examples_reviewer")
		self.executor = workflow.compile()
	
		
		
		
	def example_creator(self, state: TPTDState) -> TPTDState:
		system_prompt = read_prompt_file("create_examples")
		system_prompt = system_prompt.replace("ToolX",state["target_tool"])
		user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nPolicy Name:{state['policy_name']}"
		response = llm.chat_json(generate_messages(system_prompt, user_content))
		#policy_name = state["policy_name"]
		policy_num = state["policy_num"]
		tptd = state["TPTD"]
		target_policy = tptd["policies"][policy_num]
		target_policy["examples"] = response
		state.update({"TPTD": tptd, "iteration": 0})
		save_output(state["outdir"], f"{state['target_tool']}_{state['policy_name']}_0.json", tptd)
		return state

	def example_reviewer(self, state: TPTDState) -> TPTDState:
		system_prompt = read_prompt_file("examples_reviewer")
		user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nTPTD: {json.dumps(state['TPTD'])}\nPolicy Name:{state['policy_name']}"
		response = llm.chat_json(generate_messages(system_prompt, user_content))
		state.update({"review_score": response["global_score"], "review_comments": response["review"], "iteration": state["iteration"] + 1})
		save_output(state["outdir"], f"{state['target_tool']}_review_coverage_{state['policy_name']}_{state['iteration']}.json", response)
		return state

	def example_fixer(self, state: TPTDState) -> TPTDState:
		system_prompt = read_prompt_file("examples_fixer")
		user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nTPTD: {json.dumps(state['TPTD'])}\nReview Comments: {json.dumps(state['review_comments'])}\nPolicy Name:{state['policy_name']}"
		response = llm.chat_json(generate_messages(system_prompt, user_content))
		state.update({"TPTD": response})
		save_output(state["outdir"], f"{state['target_tool']}_fix_coverage_{state['policy_name']}_{state['iteration']}.json", response)
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
	with open(functions_schema, 'r') as file:
		functions =  json.load(file)
	
	fsummary = {}
	for k, v in functions.items():
		fsummary[k] = v['description']
	
	for function_name, function_data in functions.items():
		fname = function_data["name"]
		tptd_file = os.path.join(outdir,"final",fname+'.json')
		with open(tptd_file ) as f:
			tptd = json.load(f)
			if isinstance(tptd["policies"], str):
				continue
			for ind,p in enumerate(tptd["policies"]):
				pname = p["policy_name"]
				pdescription = p["description"]
		
				input_state = {
								"policy_text": policy_text,
								"tools": fsummary,
								"target_tool": fname,
								"target_tool_description": function_data,
								"outdir":os.path.join(outdir,"process"),
								"policy_name" :pname,
								"policy_num": ind,
								"TPTD":tptd
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
			# 					"outdir":os.path.join(outdir,"process")
			# 				}
			# 				break
				
				example_process = AddExamples()
				final_output = example_process.executor.invoke(input_state)
				print(json.dumps(final_output))
				tmpoutdir = os.path.join(outdir,"final","examples")
				outcontent = final_output["TPTD"]
				
				#out = json.loads(outcontent)
				with open(os.path.join(tmpoutdir, fname +  ".json"), "w") as outfile:
					outfile.write(json.dumps(outcontent))
