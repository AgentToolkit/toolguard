import argparse
import json
import os


import langgraph
from langgraph.graph import StateGraph
from typing import Dict, List, Any, Optional
from langchain.schema import SystemMessage, HumanMessage

from azure_wrapper import AzureWrepper

llm = AzureWrepper()


class TPTDState(Dict[str, Any]):
	policy_text: str
	tools: List[str]
	target_tool: str
	target_tool_description: Dict
	TPTD: Optional[Dict]
	review_comments: Optional[str]
	review_score:Optional[int]
	iteration: int
	next_step: str
	outdir: str
	

class Phase2:
	
	def __init__(self):
		workflow = StateGraph(TPTDState)
		
		workflow.add_node("creator", Phase2.creator_node)
		workflow.add_node("reviewer", Phase2.reviewer_node)
		workflow.add_node("fixer", Phase2.fixer_node)
		workflow.add_node("final", lambda state: state)
		
		workflow.set_entry_point("creator")
		workflow.add_edge("creator", "reviewer")
		#workflow.add_edge("reviewer", "fixer")
		workflow.add_conditional_edges("reviewer", lambda state: state["next_step"],
									   {"fixer": "fixer", "final": "final"})
		workflow.add_conditional_edges("fixer", lambda state: state["next_step"],
									   {"reviewer": "reviewer", "final": "final"})
		
		self.executor = workflow.compile()

	



	def creator_node(state: TPTDState) -> TPTDState:
		policy_text = state["policy_text"]
		tools = state["tools"]
		target_tool = state["target_tool"]
		tool_desc = state["target_tool_description"]
		outdir = state["outdir"]
		
		sys_prompt_file = os.path.join(os.path.dirname(__file__), "prompts", "policies_summary")
		with open(sys_prompt_file, "r") as f:
			system_prompt = f.read()
		messages = []
		messages.append({"role": "system", "content": system_prompt})
		messages.append({"role": "user",
						  "content": "Policy Document:" + policy_text + "\nTools Descriptions:" + json.dumps(
							  tools) + "\nTarget Tool:" + json.dumps(tool_desc)})
		
		response = llm.chat_json(messages)
		print(response)
		#res = response.strip("```json").strip("```").strip()
		#res = json.loads(res)
		state["TPTD"] = response
		state["iteration"] = 0
		with open(os.path.join(outdir,target_tool+"_"+str(state["iteration"])+".json"), "w") as outfile:
			outfile.write(json.dumps(response))
		
		return state
	
	
	def reviewer_node(state: TPTDState) -> TPTDState:
		policy_text = state["policy_text"]
		tools = state["tools"]
		target_tool = state["target_tool"]
		tool_desc = state["target_tool_description"]
		tptd = state["TPTD"]
		# todo: add more details about target tool
		outdir = state["outdir"]
		
		sys_prompt_file = os.path.join(os.path.dirname(__file__), "prompts", "policies_reviewer")
		with open(sys_prompt_file, "r") as f:
			system_prompt = f.read()
		messages = []
		messages.append({"role": "system", "content": system_prompt})
		messages.append({"role": "user",
						 "content": "Policy Document:" + policy_text + "\nTools Descriptions:" + json.dumps(
							 tools) + "\nTarget Tool:" + json.dumps(tool_desc)+"\nTPTD: "+json.dumps(tptd)})
		
		response = llm.chat_json(messages)
		print(response)
		#res = json.loads(response)
		state["review_score"] = response["Final Score"]
		state["review_comments"] = response["review"]
		state["iteration"] = state["iteration"]+1
		with open(os.path.join(outdir, target_tool + "_review_" + str(state["iteration"]) + ".json"), "w") as outfile:
			outfile.write(json.dumps(response))
		
		review_score = state["review_score"]
		if review_score["score"] == 5:
			state["next_step"] = "final"
		else:
			state["next_step"] = "fixer"
		
		return state
		
	
	
	def fixer_node(state: TPTDState) -> TPTDState:
		policy_text = state["policy_text"]
		tools = state["tools"]
		target_tool = state["target_tool"]
		tool_desc = state["target_tool_description"]
		tptd = state["TPTD"]
		# todo: add more details about target tool
		outdir = state["outdir"]
		review_comments = state["review_comments"]
		
		
		sys_prompt_file = os.path.join(os.path.dirname(__file__), "prompts", "policies_fixer")
		with open(sys_prompt_file, "r") as f:
			system_prompt = f.read()
		messages = []
		messages.append({"role": "system", "content": system_prompt})
		messages.append({"role": "user",
						 "content": "Policy Document:" + policy_text + "\nTools Descriptions:" + json.dumps(
							 tools) + "\nTarget Tool:" + json.dumps(tool_desc) + "\nTPTD: " + json.dumps(tptd)+ "\nReview Comments: " + json.dumps(review_comments)})
		
		response = llm.chat_json(messages)
		print(response)
		#print(response)
		#res = response.strip("```json").strip("```").strip()
		#res = json.loads(res)
		state["TPTD"] = response
		with open(os.path.join(outdir, target_tool + "_fix_" + str(state["iteration"]) + ".json"), "w") as outfile:
			outfile.write(json.dumps(response))
	
		# Ensure a valid next step
		if state["iteration"] < 5:
			state["next_step"] = "reviewer"
		else:
			state["next_step"] = "final"
		
		return state




if __name__ == '__main__':
	
	parser = argparse.ArgumentParser(description='parser')
	parser.add_argument('--policy-path', type=str,default='/Users/naamazwerdling/workspace/tau-bench/tau_bench/envs/airline/wiki.md')
	parser.add_argument('--outdir', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/lc/tau_airline_res/')
	parser.add_argument('--functions-schema', type=str, default='/Users/naamazwerdling/Documents/OASB/policy_validation/tau_airline_res/fc_schema.json')
	args = parser.parse_args()
	policy_path = args.policy_path
	outdir = args.outdir
	functions_schema = args.functions_schema

	policy_text = open(policy_path, 'r').read()
	with open(functions_schema, 'r') as file:
		functions =  json.load(file)
	
	fsummary = {}
	for k, v in functions.items():
		fsummary[k] = v['description']
	
	for function_name, function_data in functions.items():
		fname = function_data["name"]
		# print(fname)
		# if fname!="UpdateReservationBaggages":
		# 	continue
		
		input_state = {
			"policy_text": policy_text,
			"tools": fsummary,
			"target_tool": fname,
			"target_tool_description": function_data,
			"outdir":outdir
		}
		p2 = Phase2()
		final_output = p2.executor.invoke(input_state)
		print(json.dumps(final_output))
		tmpoutdir = "/Users/naamazwerdling/Documents/OASB/policy_validation/tau_airline_res_temp"
		outcontent = final_output["TPTD"]
		
		#out = json.loads(outcontent)
		with open(os.path.join(tmpoutdir, fname +  ".json"), "w") as outfile:
			outfile.write(json.dumps(outcontent))
