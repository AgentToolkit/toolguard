import argparse
import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from toolguard.llm.tg_litellm import LitellmModel
from toolguard.llm.tg_llm import TG_LLM
# from toolguard.stages_tptd.create_oas_summary import OASSummarizer
from toolguard.stages_tptd.utils import read_prompt_file, generate_messages, save_output, find_mismatched_references

class ToolInfo(BaseModel):
	name: str
	description: str
	parameters: Any

class TextToolPolicyGenerator:
	def __init__(self, llm:TG_LLM, policy_document:str, tools:List[ToolInfo], out_dir:str) -> None:
		self.llm = llm
		self.policy_document = policy_document
		self.tools_descriptions = {tool.name: tool.description for tool in tools}
		self.tools_details = {tool.name: tool for tool in tools}
		self.out_dir = out_dir
	
	async def generate_minimal_policy(self, tool_name:str)->dict:
		tptd = await self.create_policy(tool_name)
		tptd = await self.example_creator(tool_name,tptd)
		return tptd
		
	async def generate_policy(self, tool_name: str)->dict:
		tptd = await self.create_policy(tool_name)
		for i in range(3):
			tptd = await self.add_policies(tool_name, tptd, i)
		tptd = await self.split(tool_name, tptd)
		tptd = await self.merge(tool_name, tptd)
		tptd = await self.review_policy(tool_name, tptd)
		tptd = await self.add_references(tool_name, tptd)
		tptd = await self.reference_correctness(tool_name, tptd)
		tptd = await self.example_creator(tool_name, tptd)
		for i in range(5): #FIXME
			tptd = await self.add_examples(tool_name, tptd, i)
		tptd = await self.merge_examples(tool_name, tptd)
		#tptd = self.fix_examples(tool_name, tptd)
		tptd = await self.review_examples(tool_name, tptd)
		return tptd
		
		
	async def create_policy(self, tool_name:str) -> dict:
		print("policy_creator_node")
		system_prompt = read_prompt_file("create_policy")
		system_prompt = system_prompt.replace("ToolX",tool_name)
		user_content = f"Policy Document:{self.policy_document}\nTools Descriptions:{json.dumps(self.tools_descriptions)}\nTarget Tool:{self.tools_details[tool_name].model_dump_json()}\n"
		tptd = await self.llm.chat_json(generate_messages(system_prompt, user_content))
		save_output(self.out_dir, f"{tool_name}.json", tptd)
		return tptd
	
	

	async def add_policies(self, tool_name:str, tptd:dict, iteration:int=0) -> dict:
		print("add_policy")
		system_prompt = read_prompt_file("add_policies")
		user_content = f"Policy Document:{self.policy_document}\nTools Descriptions:{json.dumps(self.tools_descriptions)}\nTarget Tool:{self.tools_details[tool_name].model_dump_json()}\nTPTD: {json.dumps(tptd)}"
		response = await self.llm.chat_json(generate_messages(system_prompt, user_content))

		policies = response["additionalProperties"]["policies"] \
			if "additionalProperties" in response and "policies" not in response \
			else response["policies"]

		for policy in policies:
		#for policy in response["policies"]:
			policy["iteration"] = iteration
			tptd["policies"].append(policy)
		
		save_output(self.out_dir, f"{tool_name}_ADD_{iteration}.json", tptd)
		return tptd
	

	async def split(self, tool_name,tptd:dict) -> dict:
		# todo: consider addition step to split policy by policy and not overall
		print("split")
		system_prompt = read_prompt_file("split")
		user_content = f"Policy Document:{self.policy_document}\nTools Descriptions:{json.dumps(self.tools_descriptions)}\nTarget Tool:{self.tools_details[tool_name].model_dump_json()}\nTPTD: {json.dumps(tptd)}"
		tptd = await self.llm.chat_json(generate_messages(system_prompt, user_content))
		save_output(self.out_dir, f"{tool_name}_split.json", tptd)
		return tptd
	
	async def merge(self, tool_name,tptd:dict) -> dict:
		# todo: consider addition step to split policy by policy and not overall
		print("merge")
		system_prompt = read_prompt_file("merge")
		user_content = f"Policy Document:{self.policy_document}\nTools Descriptions:{json.dumps(self.tools_descriptions)}\nTarget Tool:{self.tools_details[tool_name].model_dump_json()}\nTPTD: {json.dumps(tptd)}"
		tptd = await self.llm.chat_json(generate_messages(system_prompt, user_content))
		
		save_output(self.out_dir, f"{tool_name}_merge.json", tptd)
		return tptd

	
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
			
	
	
	async def review_policy(self, tool_name,tptd) -> dict:
		print("review_policy")
		system_prompt = read_prompt_file("policy_reviewer")
		newTPTD = {"policies":[]}

		if 'policies' not in tptd:
			tptd['policies'] = []

		for policy in tptd["policies"]:
			reviews = []
			for iteration in range(5):
				user_content = f"Policy Document:{self.policy_document}\nTools Descriptions:{json.dumps(self.tools_descriptions)}\nTarget Tool:{json.dumps(self.tools_descriptions[tool_name])}\npolicy: {json.dumps(policy)}"
				response = await self.llm.chat_json(generate_messages(system_prompt, user_content))
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
		save_output(self.out_dir, f"{tool_name}_rev.json", newTPTD)
		return newTPTD
	
	async def add_references(self, tool_name:str,tptd:dict) -> dict:
		print("add_ref")
		system_prompt = read_prompt_file("add_references")
		#remove old refs (used to help avoid duplications)
		for policy in tptd["policies"]:
			policy["references"] = []
			user_content = f"Policy Document:{self.policy_document}\nTools Descriptions:{json.dumps(self.tools_descriptions)}\nTarget Tool:{self.tools_details[tool_name].model_dump_json()}\npolicy: {json.dumps(policy)}"
			response = await self.llm.chat_json(generate_messages(system_prompt, user_content))
			if "references" in response:
				policy["references"] = response["references"]
			else:
				print("Error! no references in response")
				print(response)
			
		
		save_output(self.out_dir, f"{tool_name}_ref.json", tptd)
		return tptd

	async def reference_correctness(self, tool_name:str,tptd:dict) -> dict:
		print("reference_correctness")
		tptd, unmatched_policies = find_mismatched_references(self.policy_document,tptd)
		save_output(self.out_dir, f"{tool_name}_ref_orig_.json", unmatched_policies)
		save_output(self.out_dir, f"{tool_name}_ref_correction_.json", tptd)
		return tptd
	
	async def example_creator(self, tool_name:str,tptd:dict) -> dict:
		print("example_creator")
		system_prompt = read_prompt_file("create_examples")
		system_prompt = system_prompt.replace("ToolX",tool_name)
		
		for policy in tptd["policies"]:
			#user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nPolicy:{policy}"
			user_content = f"Tools Descriptions:{json.dumps(self.tools_descriptions)}\nTarget Tool:{self.tools_details[tool_name].model_dump_json()}\nPolicy:{policy}"
			
			response = await self.llm.chat_json(generate_messages(system_prompt, user_content))
			if 'violating_examples' in response:
				policy["violating_examples"] = response["violating_examples"]
				
			if 'compliance_examples' in response:
				policy["compliance_examples"] = response["compliance_examples"]
		
		save_output(self.out_dir, f"{tool_name}_examples.json", tptd)
		return tptd
	
	async def add_examples(self, tool_name:str,tptd:dict,iteration:int) -> dict:
		print("add_examples")
		system_prompt = read_prompt_file("add_examples")
		system_prompt = system_prompt.replace("ToolX", tool_name)
		for policy in tptd["policies"]:
			#user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nPolicy:{policy}"
			user_content = f"Tools Descriptions:{json.dumps(self.tools_descriptions)}\nTarget Tool:{self.tools_details[tool_name].model_dump_json()}\nPolicy:{policy}"
			response = await self.llm.chat_json(generate_messages(system_prompt, user_content))
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
		
		save_output(self.out_dir, f"{tool_name}_ADD_examples{iteration}.json", tptd)
		return tptd
	
	async def merge_examples(self,tool_name:str,tptd:dict) -> dict:
		print("merge_examples")
		system_prompt = read_prompt_file("merge_examples")
		system_prompt = system_prompt.replace("ToolX", tool_name)
		for policy in tptd["policies"]:
			#user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nPolicy Name:{policy['policy_name']}\nPolicy Description:{policy['description']}"
			user_content = f"Tools Descriptions:{json.dumps(self.tools_descriptions)}\nTarget Tool:{self.tools_details[tool_name].model_dump_json()}\nPolicy Name:{policy['policy_name']}\nPolicy Description:{policy['description']}"
			user_content+= f"\n\nViolating Examples: {policy['violating_examples']}"
			user_content+= f"\n\nCompliance Examples: {policy['compliance_examples']}"
			response = await self.llm.chat_json(generate_messages(system_prompt, user_content))
			policy["violating_examples"] = response["violating_examples"]
			policy["compliance_examples"] = response["compliance_examples"]

		
		save_output(self.out_dir, f"{tool_name}_merge_examples.json", tptd)
		return tptd
	
	async def fix_examples(self, tool_name:str,tptd:dict) -> dict:
		print("fix_examples")
		orig_prompt = read_prompt_file("fix_example")
		for policy in tptd["policies"]:
			for etype in ["violating","compliance"]:
				fixed_examples = []
				for example in policy[etype + "_examples"]:
					system_prompt = orig_prompt.replace("ToolX", tool_name)
					system_prompt = system_prompt.replace("__EXAMPLE_TYPE__", "")
			
					#user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nPolicy Name:{policy['policy_name']}\nPolicy Description:{policy['description']}\nExample:{example}"
					user_content = f"Tools Descriptions:{json.dumps(self.tools_descriptions)}\nTarget Tool:{self.tools_details[tool_name].model_dump_json()}\nPolicy Name:{policy['policy_name']}\nPolicy Description:{policy['description']}\nExample:{example}"
					
					response = await self.llm.chat_json(generate_messages(system_prompt, user_content))
					fixed_examples.append(response["revised_example"])
				policy[etype + "_examples"] = fixed_examples
		
	
		save_output(self.out_dir, f"{tool_name}_fix_examples.json", tptd)
		return tptd
	
	#todo: change to revew examples, write prompts
	async def review_examples(self, tool_name:str,tptd:dict) -> dict:
		print("review_examples")
		system_prompt = read_prompt_file("examples_reviewer")
		for policy in tptd["policies"]:
			print(policy['policy_name'])
			for etype in ["violating","compliance"]:
				print(etype)
				passed_examples = []
				for example in policy[etype + "_examples"]:
					print(example)
					reviews = []
					for iteration in range(5):
						#user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nPolicy Name:{policy['policy_name']}\nPolicy Description:{policy['description']}\nExample:{example}"
						user_content = f"Tools Descriptions:{json.dumps(self.tools_descriptions)}\nTarget Tool:{self.tools_details[tool_name].model_dump_json()}\nPolicy Name:{policy['policy_name']}\nPolicy Description:{policy['description']}\nExample:{example}"
						response = await self.llm.chat_json(generate_messages(system_prompt, user_content))
						reviews.append(response)
					keep = self.keep_example(reviews)
					if keep:
						passed_examples.append(example)
				
				policy[etype + "_examples"] = passed_examples
		
		
		save_output(self.out_dir, f"{tool_name}_example_rev.json", tptd)
		return tptd
	
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

async def step1_main(policy_text:str, tools:List[ToolInfo], step1_output_dir:str, llm:TG_LLM, tools_shortlist: Optional[List[str]]=None, short1=False):
	if not os.path.isdir(step1_output_dir):
		os.makedirs(step1_output_dir)
		
	process_dir = os.path.join(step1_output_dir, "process")
	if not os.path.isdir(process_dir):
		os.makedirs(process_dir)
	
	tpg = TextToolPolicyGenerator(llm, policy_text, tools, process_dir)
	async def do_one_tool(fname):
		if short1:
			final_output = await tpg.generate_minimal_policy(fname)
		else:
			final_output = await tpg.generate_policy(fname)

		with open(os.path.join(step1_output_dir, fname + ".json"), "w") as outfile1:
			outfile1.write(json.dumps(final_output, indent=2))

	await asyncio.gather(*[do_one_tool(tool.name) for tool in tools if ((tools_shortlist is None) or (tool.name in tools_shortlist))])
	print("All tools done")


# async def step1_main_with_tools(policy_text:str, tools, step1_output_dir:str, llm:TG_LLM, tools2run:Optional[List[str]]=None, short1=False):
# 	tools_descriptions = {}
# 	tools_details = {}
# 	for tool in tools:
# 		name = tool.name
# 		description = tool.__doc__.strip() if tool.__doc__ else ""
# 		tools_descriptions[name] = description
# 		parameters = tool.args_schema.model_json_schema()
# 		tools_details[name] = {
# 			"name": name,
# 			"description": description,
# 			"parameters": parameters
# 		}

# 	await step1_main(policy_text, tools_descriptions, tools_details, step1_output_dir, llm, tools2run, short1)

if __name__ == '__main__':
	import dotenv
	dotenv.load_dotenv()
	
	import markdown
	parser = argparse.ArgumentParser(description='parser')
	parser.add_argument('--model-name', type=str,default='gpt-4o-2024-08-06')
	parser.add_argument('--policy-path', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/wiki.md')
	parser.add_argument('--oas', type=str, help='Path to OAS file')
	parser.add_argument('--tools-info-path', type=str, help='Path to tools info JSON file')
	parser.add_argument('--out-dir', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/outdir2/step1_out')
	parser.add_argument('--tools', nargs='+', default=None, help='Optional list of tool names. These are a subset of the tools in the openAPI operation ids.')
	parser.add_argument('--short-step1', action='store_true', default=False, help='run short version of step 1')
	args = parser.parse_args()
	if not args.oas and not args.tools_info_path:
		parser.error("You must provide at least one of --oas or --tools-info-path")
	
	policy_path = args.policy_path
	out_dir = args.out_dir
	policy_text = open(policy_path, 'r',encoding='utf-8').read()
	policy_text = markdown.markdown(policy_text)
	
	# tools_descriptions = {}
	tools_details = {}
	# if args.oas:
	# 	with open(args.oas, 'r', encoding='utf-8') as file:
	# 		oas = json.load(file)
	# 	summarizer = OASSummarizer(oas)
	# 	tools_details = summarizer.summarize()
	# 	tools_descriptions = {k: v["description"] for k, v in tools_details.items()}
	# else:
	tools_info_path = args.tools_info_path
	with open(tools_info_path, 'r', encoding='utf-8') as file:
		data = json.load(file)
		tools_info = [ToolInfo(**item) for item in data]
	# for t in tools_info:
	# 	func = t["function"]
	# 	name = func["name"]
	# 	description = func["description"]
	# 	# tools_descriptions[name] = description
	# 	tools_details[name] = func
	
	# for k in tools_details.keys():
	# 	print(k)
	llm = LitellmModel(args.model_name)
	
	asyncio.run(
		step1_main(policy_text, tools_info, args.out_dir, llm, args.tools, args.short_step1)
	)
	

