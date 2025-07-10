import json
import os

import dotenv

from toolguard.llm.tg_litellm import LitellmModel

dotenv.load_dotenv()
model = "gpt-4o-2024-08-06"
aw = LitellmModel(model)
input_file = "/Users/naamazwerdling/Documents/OASB/policy_validation/orca/prompts_structured.json"
output_dir = "/Users/naamazwerdling/Documents/OASB/policy_validation/orca/"
prompt = "Assume the following tools are available and below each tool listed the pre-conditions to test before invoking the tool. Please write a policy document based on those rules. Do not mention explicitly the tool name but rather use text to describe the action and the pre-conditions as a policy document. the response should not be so structured but more similar to unstructured text. please write in markdown format"
expl = "The constraints are organized hierarchically: - 'ALL of these conditions must be met' indicates that every listed condition is required (AND logic) - 'ANY ONE of these conditions must be met' indicates that at least one condition is required (OR logic) - 'These steps must be completed in order' indicates a sequence that must be followed (CHAIN logic) Numbered items (1., 2., etc.) represent ordered steps, while bulleted items (•) represent unordered conditions. You must verify all required conditions in their specified structure before performing an action.\n\n### Actions with Constraints:"
with open(input_file, 'r') as file:
	data = json.load(file)
for domain, text in data.items():
	rules = text.split("### Actions with Constraints:")[1]
	dir = os.path.join(output_dir, domain)
	if not os.path.isdir(dir):
		os.makedirs(dir)
	
	resp = aw.generate([{"role": "system", "content": prompt},
						 {"role": "user", "content": expl + "\n"+rules}])
	with open(os.path.join(output_dir, domain,  "policy.md"), "w") as outfile:
		json.dump(resp, outfile, indent=4)
	