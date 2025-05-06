import argparse
import json
import os
from typing import List, Dict

import markdown

from langgraph.graph import StateGraph

from policy_adherence.common.open_api import OpenAPI
from policy_adherence.llm.azure_wrapper import AzureLitellm
from policy_adherence.stages_tptd.utils import read_prompt_file, generate_messages, save_output, TPTDState, \
	find_mismatched_references
from tests.op_only_oas import op_only_oas

model = 'gpt-4o-2024-08-06'
llm = AzureLitellm(model)

class PolicyIdentifier:
	def __init__(self):
		workflow = StateGraph(TPTDState)
		workflow.add_node("policy_creator", self.policy_creator_node)
		#workflow.add_node("merge_and_split",self.merge_and_split)
		workflow.add_node("split", self.split)
		workflow.add_node("merge", self.merge)
		workflow.add_node("review_policy",self.review_policy)
		workflow.add_node("add_policies", self.add_policies)
		workflow.add_node("add_references",self.add_references)
		workflow.add_node("reference_correctness", self.reference_correctness)
		workflow.add_node("example_creator", self.example_creator)
		workflow.add_node("add_examples",self.add_examples)
		workflow.add_node("final", lambda state: state)
		
		workflow.set_entry_point("policy_creator")
		
		workflow.add_edge("policy_creator", "add_policies")
		#workflow.add_conditional_edges("add_policies", lambda state: "merge_and_split" if state.get("stop", False) else "add_policies" )
		#workflow.add_edge("merge_and_split", "review_policy")
		workflow.add_conditional_edges("add_policies",lambda state: "split" if state.get("stop", False) else "add_policies")
		workflow.add_edge("split", "merge")
		workflow.add_edge("merge", "review_policy")
		workflow.add_edge("review_policy", "add_references")
		workflow.add_edge("add_references", "reference_correctness")
		workflow.add_edge("reference_correctness", "example_creator")
		workflow.add_edge("example_creator", "add_examples")
		workflow.add_conditional_edges("add_examples",lambda state: "final" if state.get("stop", False) else "add_examples")
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
	
	

	def add_policies(self, state: TPTDState) -> TPTDState:
		print("add_policy")
		system_prompt = read_prompt_file("add_policies")
		TPTD = state['TPTD']
		user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nTPTD: {json.dumps(TPTD)}"
		response = llm.chat_json(generate_messages(system_prompt, user_content))
		for policy in response["policies"]:
			policy["iteration"] = state["iteration"]
			TPTD["policies"].append(policy)
			
		state.update({"TPTD": TPTD, "iteration": state["iteration"] + 1})
		if state["iteration"]>3:
			state.update({"stop":True})
		save_output(state["outdir"], f"{state['target_tool']}_ADD_{state['iteration']}.json", TPTD)
		return state
	

	def split(self, state: TPTDState) -> TPTDState:
		# todo: consider addition step to split policy by policy and not overall
		print("split")
		system_prompt = read_prompt_file("split")
		TPTD = state['TPTD']
		user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nTPTD: {json.dumps(TPTD)}"
		response = llm.chat_json(generate_messages(system_prompt, user_content))
		TPTD = response
		
		state.update({"TPTD": TPTD})
		save_output(state["outdir"], f"{state['target_tool']}_split.json", TPTD)
		return state
	
	def merge(self, state: TPTDState) -> TPTDState:
		# todo: consider addition step to split policy by policy and not overall
		print("merge")
		system_prompt = read_prompt_file("merge")
		TPTD = state['TPTD']
		user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nTPTD: {json.dumps(TPTD)}"
		response = llm.chat_json(generate_messages(system_prompt, user_content))
		TPTD = response
		
		state.update({"TPTD": TPTD})
		save_output(state["outdir"], f"{state['target_tool']}_merge.json", TPTD)
		return state

	
	def merge_and_split(self, state: TPTDState) -> TPTDState:
		#todo: consider addition step to split policy by policy and not overall
		print("merge_and_split")
		system_prompt = read_prompt_file("merge_and_split")
		TPTD = state['TPTD']
		user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nTPTD: {json.dumps(TPTD)}"
		response = llm.chat_json(generate_messages(system_prompt, user_content))
		TPTD = response
		
		state.update({"TPTD": TPTD})
		save_output(state["outdir"], f"{state['target_tool']}_sam.json", TPTD)
		return state
	
	def move2archive(self, reviews) -> (bool,str):
		comments = ""
		num = len(reviews)
		if num == 0:
			return False
		counts = {
			"is_relevant": 0,
			"is_tool_specific": 0,
			"can_be_validated": 0,
			"is_actionable": 0
		}
		
		for r in reviews:
			print(f"{r['is_relevant'] if 'is_relevant' in r else ''}\t{r['is_tool_specific'] if 'is_tool_specific' in r else ''}\t{r['can_be_validated'] if 'can_be_validated' in r else ''}\t{r['is_actionable'] if 'is_actionable' in r else ''}\t{r['is_self_contained'] if 'is_self_contained' in r else ''}\t{r['score'] if 'score' in r else ''}\t")

			counts["is_relevant"] += r["is_relevant"]
			counts["is_tool_specific"] += r["is_tool_specific"]
			counts["can_be_validated"] += r["can_be_validated"]
			counts["is_actionable"] += r["is_actionable"]
			if not( r['is_relevant'] and r['is_tool_specific'] and r['can_be_validated'] and r['is_actionable']):
				comments+= r["comments"]+"\n"

		return not(all(float(counts[key]) / num > 0.5 for key in counts)),comments
			
	
	
	def review_policy(self, state: TPTDState) -> TPTDState:
		print("review_policy")
		system_prompt = read_prompt_file("policy_reviewer")
		TPTD = state["TPTD"]
		newTPTD = {"policies":[]}
		for policy in TPTD["policies"]:
			reviews = []
			for iteration in range(5):
				user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\npolicy: {json.dumps(policy)}"
				response = llm.chat_json(generate_messages(system_prompt, user_content))
				is_self_contained = response["is_self_contained"]
				if not is_self_contained:
					policy["description"] = response["alternative_description"]
				reviews.append(response)
			archive,comments = self.move2archive(reviews)
			print(archive)
			if archive:
				if "archive" not in newTPTD:
					newTPTD["archive"] = []
				policy["comments"] = comments
				newTPTD["archive"].append(policy)
			else:
				newTPTD["policies"].append(policy)
				
		state.update({"TPTD": newTPTD})
		save_output(state["outdir"], f"{state['target_tool']}_rev.json", newTPTD)
		return state
	
	def add_references(self, state: TPTDState) -> TPTDState:
		print("add_ref")
		system_prompt = read_prompt_file("add_references")
		#remove old refs (used to help avoid duplications)
		TPTD = state["TPTD"]
		for policy in TPTD["policies"]:
			policy["references"] = []
			user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\npolicy: {json.dumps(policy)}"
			response = llm.chat_json(generate_messages(system_prompt, user_content))
			policy["references"] = response["references"]
			
		state.update({"TPTD": TPTD})
		save_output(state["outdir"], f"{state['target_tool']}_ref.json", TPTD)
		return state

	def reference_correctness(self, state: TPTDState) -> TPTDState:
		print("reference_correctness")
		policy_text = state["policy_text"]
		tptd = state["TPTD"]
		corrections, unmatched_policies = find_mismatched_references(policy_text,tptd)
		state["TPTD"] = corrections
		state["reference_mismatch"] = unmatched_policies
		state["iteration"] =  state["iteration"] + 1
		save_output(state["outdir"], f"{state['target_tool']}_ref_orig_.json", unmatched_policies)
		return state
	
	def example_creator(self, state: TPTDState) -> TPTDState:
		print("example_creator")
		system_prompt = read_prompt_file("create_examples")
		system_prompt = system_prompt.replace("ToolX", state["target_tool"])
		TPTD = state["TPTD"]
		for policy in TPTD["policies"]:
			user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nPolicy:{policy}"
			response = llm.chat_json(generate_messages(system_prompt, user_content))
			if 'violating_examples' in response:
				policy["violating_examples"] = response["violating_examples"]
				
			if 'compliance_examples' in response:
				policy["compliance_examples"] = response["compliance_examples"]
		state.update({"TPTD": TPTD, "iteration": 0,"stop":False})
		save_output(state["outdir"], f"{state['target_tool']}_examples.json", TPTD)
		return state
	
	def add_examples(self, state: TPTDState) -> TPTDState:
		print("add_examples")
		system_prompt = read_prompt_file("add_examples")
		system_prompt = system_prompt.replace("ToolX", state["target_tool"])
		TPTD = state["TPTD"]
		for policy in TPTD["policies"]:
			user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nPolicy:{policy}"
			response = llm.chat_json(generate_messages(system_prompt, user_content))
			if 'violating_examples' in response:
				for vexample in response["violating_examples"]:
					#vexample["iteration"] = state["iteration"]
					if "violating_examples" not in policy:
						policy["violating_examples"] = []
					policy["violating_examples"].append(vexample)
			if 'compliance_examples' in response:
				for cexample in response["compliance_examples"]:
					if "compliance_examples" not in policy:
						policy["compliance_examples"] = []
					#cexample["iteration"] = state["iteration"]
					policy["compliance_examples"].append(cexample)
				
		state.update({"TPTD": TPTD, "iteration": state["iteration"] + 1})
		if state["iteration"] > 3:
			state.update({"stop": True})
		save_output(state["outdir"], f"{state['target_tool']}_ADD_examples{state['iteration']}.json", TPTD)
		return state
	
def step1_main(policy_text:str,fsummary:Dict,fdetails:Dict,outdir:str):
	for fname, detail in fdetails.items():
		input_state = {
			"policy_text": policy_text,
			"tools": fsummary,
			"target_tool": fname,
			"target_tool_description": detail,
			"outdir": os.path.join(outdir, "process")
		}
		p2 = PolicyIdentifier()
		final_output = p2.executor.invoke(input_state)
		print(json.dumps(final_output))
		tmpoutdir = os.path.join(outdir, "final")
		outcontent = final_output["TPTD"]
		
		with open(os.path.join(tmpoutdir, fname + ".json"), "w") as outfile:
			outfile.write(json.dumps(outcontent))
	


if __name__ == '__main__':
	
	parser = argparse.ArgumentParser(description='parser')
	#parser.add_argument('--model-type', type=str,default='ASURE')
	#parser.add_argument('--model-name', type=str,default='gpt-4o-2024-08-06')
	#parser.add_argument('--policy-path', type=str, default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/wiki-with-policies-for-non-existing-tools-rev.md')
	#parser.add_argument('--policy-path',type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/wiki-with-policies-for-non-existing-tools.md')
	parser.add_argument('--policy-path', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/wiki.md')
	parser.add_argument('--outdir', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline')

	parser.add_argument('--oas', type=str, default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/airline.json')
	parser.add_argument('--functions-schema', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/fc_schema.json')

	args = parser.parse_args()
	policy_path = args.policy_path
	outdir = args.outdir
	#model_type = args.model_type
	#model_name = args.model_name
	functions_schema = args.functions_schema
	oas = args.oas

	policy_text = open(policy_path, 'r',encoding='utf-8').read()
	policy_text = markdown.markdown(policy_text)

	fsummary = {}
	fdetails = {}
	if functions_schema:
		with open(functions_schema,'r',encoding='utf-8') as file:
			functions = json.load(file)
		for k, v in functions.items():
			fsummary[k] = v['description']
		print(json.dumps(fsummary))
		fdetails = functions
	else:
		with open(oas,'r',encoding='utf-8') as file:
			functions = json.load(file)

		if 'paths' in functions:
			for path, methods in functions["paths"].items():
				for method, details in methods.items():
					if isinstance(details, dict) and "operationId" in details:
						operation_id = details["operationId"]
						description = details.get("description", "No description available.")
						fsummary[operation_id] = description
	
			for path, methods in functions["paths"].items():
				for method, details in methods.items():
					if isinstance(details, dict) and "operationId" in details:
						fname = details["operationId"]
						oas = OpenAPI.model_validate(functions)
						op_oas = op_only_oas(oas, fname)
						print(fname)
						fdetails[fname] = op_oas
						
	step1_main(policy_text,fsummary,fdetails,outdir)
	

