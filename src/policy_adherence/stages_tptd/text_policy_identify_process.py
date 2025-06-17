import argparse
import json
import os
from typing import List, Dict, Optional

import markdown

from langgraph.graph import StateGraph

from policy_adherence.common.open_api import OpenAPI
from policy_adherence.llm.litellm_model import LitellmModel
from policy_adherence.llm.llm_model import LLM_model
from policy_adherence.stages_tptd.create_oas_summary import OASSummarizer
from policy_adherence.stages_tptd.utils import read_prompt_file, generate_messages, save_output, TPTDState, \
	find_mismatched_references
from tests.op_only_oas import op_only_oas
import dotenv
dotenv.load_dotenv()


class PolicyIdentifier:
	def __init__(self,model:str='gpt-4o-2024-08-06'):
		self.llm = LitellmModel(model)
		workflow = StateGraph(TPTDState)
		workflow.add_node("policy_creator", self.policy_creator_node)
		workflow.add_node("add_policies", self.add_policies)
		#workflow.add_node("merge_and_split",self.merge_and_split)
		workflow.add_node("split", self.split)
		workflow.add_node("merge", self.merge)
		workflow.add_node("review_policy",self.review_policy)
		workflow.add_node("add_references",self.add_references)
		workflow.add_node("reference_correctness", self.reference_correctness)
		workflow.add_node("example_creator", self.example_creator)
		workflow.add_node("add_examples",self.add_examples)
		workflow.add_node("merge_examples", self.merge_examples)
		workflow.add_node("fix_examples",self.fix_examples)
		workflow.add_node("review_examples", self.review_examples)
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
		
		#workflow.add_edge("reference_correctness", "final")
		
		
		workflow.add_edge("reference_correctness", "example_creator")
		workflow.add_edge("example_creator", "add_examples")
		workflow.add_conditional_edges("add_examples",lambda state: "merge_examples" if state.get("stop", False) else "add_examples")
		# workflow.add_edge("merge_examples", "fix_examples")
		# workflow.add_edge("fix_examples","review_examples")
		workflow.add_edge("merge_examples", "review_examples")
		workflow.add_edge("review_examples", "final")
		
		self.executor = workflow.compile()
		
		
		
		
	def policy_creator_node(self, state: TPTDState) -> TPTDState:
		print("policy_creator_node")
		system_prompt = read_prompt_file("create_policy")
		system_prompt = system_prompt.replace("ToolX",state["target_tool"])
		print(json.dumps(state['target_tool_description']))
		user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}"
		response = self.llm.chat_json(generate_messages(system_prompt, user_content))
		state.update({"TPTD": response, "iteration": 0})
		save_output(state["outdir"], f"{state['target_tool']}_0.json", response)
		return state
	
	

	def add_policies(self, state: TPTDState) -> TPTDState:
		print("add_policy")
		system_prompt = read_prompt_file("add_policies")
		TPTD = state['TPTD']
		user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nTPTD: {json.dumps(TPTD)}"
		response = self.llm.chat_json(generate_messages(system_prompt, user_content))

		policies = response["additionalProperties"]["policies"] \
			if "additionalProperties" in response and "policies" not in response \
			else response["policies"]

		for policy in policies:
		#for policy in response["policies"]:
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
		response = self.llm.chat_json(generate_messages(system_prompt, user_content))
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
		response = self.llm.chat_json(generate_messages(system_prompt, user_content))
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
		response = self.llm.chat_json(generate_messages(system_prompt, user_content))
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

			counts["is_relevant"] += (r["is_relevant"] if 'is_relevant' in r else 0)
			counts["is_tool_specific"] += (r["is_tool_specific"] if 'is_tool_specific' in r else 0)
			counts["can_be_validated"] += (r["can_be_validated"] if "can_be_validated" in r else 0)
			counts["is_actionable"] += (r["is_actionable"] if "is_actionable" in r else 0)

			if not all(e in r for e in ['is_relevant', 'is_tool_specific', 'can_be_validated', 'is_actionable']) or \
					not(r['is_relevant'] and r['is_tool_specific'] and r['can_be_validated'] and r['is_actionable']):
				comments+= r["comments"]+"\n"

		return not(all(float(counts[key]) / num > 0.5 for key in counts)),comments
			
	
	
	def review_policy(self, state: TPTDState) -> TPTDState:
		print("review_policy")
		system_prompt = read_prompt_file("policy_reviewer")
		TPTD = state["TPTD"]
		newTPTD = {"policies":[]}

		if 'policies' not in TPTD:
			TPTD['policies'] = []

		for policy in TPTD["policies"]:
			reviews = []
			for iteration in range(5):
				user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\npolicy: {json.dumps(policy)}"
				response = self.llm.chat_json(generate_messages(system_prompt, user_content))
				if "is_self_contained" in response:
					is_self_contained = response["is_self_contained"]
					if not is_self_contained:
						if "alternative_description" in response:
							policy["description"] = response["alternative_description"]
						else:
							print("Error: review is_self_contained is false but no alternative_description.")
				else:
					print("Error: review did not provide is_self_contained.")
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
			response = self.llm.chat_json(generate_messages(system_prompt, user_content))
			if "references" in response:
				policy["references"] = response["references"]
			else:
				print("Error! no references in response")
				print(response)
			
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
			#user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nPolicy:{policy}"
			user_content = f"Tools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nPolicy:{policy}"
			
			response = self.llm.chat_json(generate_messages(system_prompt, user_content))
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
			#user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nPolicy:{policy}"
			user_content = f"Tools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nPolicy:{policy}"
			response = self.llm.chat_json(generate_messages(system_prompt, user_content))
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
		if state["iteration"] > 5:
			state.update({"stop": True})
		save_output(state["outdir"], f"{state['target_tool']}_ADD_examples{state['iteration']}.json", TPTD)
		return state
	
	def merge_examples(self, state: TPTDState) -> TPTDState:
		print("merge_examples")
		system_prompt = read_prompt_file("merge_examples")
		system_prompt = system_prompt.replace("ToolX", state["target_tool"])
		TPTD = state["TPTD"]
		for policy in TPTD["policies"]:
			#user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nPolicy Name:{policy['policy_name']}\nPolicy Description:{policy['description']}"
			user_content = f"Tools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nPolicy Name:{policy['policy_name']}\nPolicy Description:{policy['description']}"
			user_content+= f"\n\nViolating Examples: {policy['violating_examples']}"
			user_content+= f"\n\nCompliance Examples: {policy['compliance_examples']}"
			response = self.llm.chat_json(generate_messages(system_prompt, user_content))
			policy["violating_examples"] = response["violating_examples"]
			policy["compliance_examples"] = response["compliance_examples"]
			
		
		state.update({"TPTD": TPTD})
		save_output(state["outdir"], f"{state['target_tool']}_merge_examples{state['iteration']}.json", TPTD)
		return state
	
	def fix_examples(self, state: TPTDState) -> TPTDState:
		print("fix_examples")
		orig_prompt = read_prompt_file("fix_example")
		TPTD = state["TPTD"]
		for policy in TPTD["policies"]:
			for etype in ["violating","compliance"]:
				fixed_examples = []
				for example in policy[etype + "_examples"]:
					system_prompt = orig_prompt.replace("ToolX", state["target_tool"])
					system_prompt = system_prompt.replace("__EXAMPLE_TYPE__", "")
			
					#user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nPolicy Name:{policy['policy_name']}\nPolicy Description:{policy['description']}\nExample:{example}"
					user_content = f"Tools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nPolicy Name:{policy['policy_name']}\nPolicy Description:{policy['description']}\nExample:{example}"
					
					response = self.llm.chat_json(generate_messages(system_prompt, user_content))
					fixed_examples.append(response["revised_example"])
				policy[etype + "_examples"] = fixed_examples
		
		state.update({"TPTD": TPTD})
		save_output(state["outdir"], f"{state['target_tool']}_fix_examples.json", TPTD)
		return state
	
	#todo: change to revew examples, write prompts
	def review_examples(self, state: TPTDState) -> TPTDState:
		print("review_examples")
		system_prompt = read_prompt_file("examples_reviewer")
		TPTD = state["TPTD"]
		for policy in TPTD["policies"]:
			print(policy['policy_name'])
			for etype in ["violating","compliance"]:
				print(etype)
				passed_examples = []
				for example in policy[etype + "_examples"]:
					print(example)
					reviews = []
					for iteration in range(5):
						#user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nPolicy Name:{policy['policy_name']}\nPolicy Description:{policy['description']}\nExample:{example}"
						user_content = f"Tools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nPolicy Name:{policy['policy_name']}\nPolicy Description:{policy['description']}\nExample:{example}"
						response = self.llm.chat_json(generate_messages(system_prompt, user_content))
						reviews.append(response)
					keep = self.keep_example(reviews)
					if keep:
						passed_examples.append(example)
				
				policy[etype + "_examples"] = passed_examples
		
		state.update({"TPTD": TPTD})
		save_output(state["outdir"], f"{state['target_tool']}_example_rev.json", TPTD)
		return state
	
	def keep_example(self, reviews) -> bool:
		bads = 0
		totals = 0
		for r in reviews:
			for vals in r.values():
				totals+=1
				if "value" not in vals:
					print(reviews)
				elif not vals["value"]:
					bads += 1
		if bads/totals > 0.8:
			return False
		return True
		
		
	

def step1_main(policy_text:str, oas:Dict, step1_output_dir:str,model, tools:Optional[List[str]]=None):
	if not os.path.isdir(step1_output_dir):
		os.makedirs(step1_output_dir)
		
	process_dir = os.path.join(step1_output_dir, "process")
	if not os.path.isdir(process_dir):
		os.makedirs(process_dir)
	
	summarizer = OASSummarizer(oas)
	summary = summarizer.summarize()
	fsummary = {k:v["description"] for k,v in summary.items()}
	for k in fsummary.keys():
		print(k)
	
	for fname, detail in summary.items():
		if tools is None or fname in tools:
			print(fname)
			print(detail)
			input_state = {
				"policy_text": policy_text,
				"tools": fsummary,
				"target_tool": fname,
				"target_tool_description": detail,
				"outdir": process_dir
			}
			p2 = PolicyIdentifier(model)
			final_output = p2.executor.invoke(input_state)
			print(json.dumps(final_output))
			#tmpoutdir = os.path.join(outdir, "final")
			outcontent = final_output["TPTD"]
			print(outcontent)
			print(os.path.join(step1_output_dir, fname + ".json"))
			with open(os.path.join(step1_output_dir, fname + ".json"), "w") as outfile1:
				outfile1.write(json.dumps(outcontent))



if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='parser')
	parser.add_argument('--model-name', type=str,default='gpt-4o-2024-08-06')
	#parser.add_argument("--model-name",type=str,default='meta-llama/llama-3-3-70b-instruct')
	#parser.add_argument('--policy-path', type=str, default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/wiki-with-policies-for-non-existing-tools-rev.md')
	#parser.add_argument('--policy-path',type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/wiki-with-policies-for-non-existing-tools.md')
	parser.add_argument('--policy-path', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/wiki.md')
	parser.add_argument('--oas', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/airline.json')
	parser.add_argument('--outdir', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/outdir2/step1_out')
	parser.add_argument('--tools', nargs='+', default=None, help='Optional list of tool names. These are a subset of the tools in the openAPI operation ids.')

	args = parser.parse_args()
	policy_path = args.policy_path
	oas_file = args.oas
	outdir = args.outdir
	
	policy_text = open(policy_path, 'r',encoding='utf-8').read()
	policy_text = markdown.markdown(policy_text)

	with open(oas_file,'r',encoding='utf-8') as file:
		oas = json.load(file)

		
	step1_main(policy_text,oas,outdir,args.model_name,args.tools)
	

