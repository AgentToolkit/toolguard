import json
import os

from policy_adherence.llm.litellm_model import LitellmModel
from policy_adherence.stages_tptd.utils import generate_messages


class GenPolicyFromRefs:
	def __init__(self,dir,policy_doc_path,tools_schema):
		with open(os.path.join(os.path.dirname(__file__), "gen_gt_policy_from_refs"), "r") as f:
			system_prompt = f.read()
		with open(policy_doc_path, "r") as f:
			policy_text = f.read()
		with open(tools_schema, 'r') as file:
			functions = json.load(file)
		fsummary = {}
		for k, v in functions.items():
			fsummary[k.replace('_','').lower().replace('.py','')] = v['description']
			
			
		model = 'gpt-4o-2024-08-06'
		llm = LitellmModel(model)
		
		
		for tool_file in os.listdir(dir):
			if tool_file.endswith(".json") :
				gt_orig_path = os.path.join(dir, tool_file)
				tools_name = tool_file.replace('.json','')
				print(tools_name)
				references = []
				with open(gt_orig_path, 'r') as file:
					policies = json.load(file)
					for p in policies["policies"]:
						references.extend([r.lower().replace("<p>", "").replace("</p>", "") for r in p["references"]])
				ground_truth_ref_path = os.path.join(dir, "refs",tool_file)
				with open(ground_truth_ref_path, "w") as outfile:
					json.dump(references, outfile, indent=4)
				ground_truth_policy_path = os.path.join(dir, "policy", tool_file)
				
				if len(references) == 0:
					with open(ground_truth_policy_path, "w") as outfile:
						json.dump("", outfile, indent=4)
					continue
				user_content = f"Policy Document:{policy_text}\nTarget Tool:{tools_name}:{fsummary[tools_name.lower()]}\nReferences: {json.dumps(references)}"
				response = llm.chat_json(generate_messages(system_prompt, user_content))
				#validate refs:
				gen_refs = []
				for p in response["policies"]:
					gen_refs.extend(p["references"])
				for r in gen_refs:
					if r not in references:
						print("adding ref: "+r)
				for r in references:
					if r not in gen_refs:
						print("missing ref: "+ r)
				
						
						
				ground_truth_policy_path =os.path.join(dir, "policy",tool_file)
				with open(ground_truth_policy_path, "w") as outfile:
					json.dump(response, outfile, indent=4)
			
	
	
	
if __name__ == '__main__':
	gtdir = '/Users/naamazwerdling/Documents/OASB/policy_validation/airline/GroundTruth'
	policy_doc = '/Users/naamazwerdling/Documents/OASB/policy_validation/airline/wiki.md'
	tools_schema = '/Users/naamazwerdling/Documents/OASB/policy_validation/airline/fc_schema.json'
	GenPolicyFromRefs(gtdir,policy_doc,tools_schema)
 