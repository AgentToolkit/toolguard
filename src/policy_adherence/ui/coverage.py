import argparse
import os
import re
from collections import defaultdict

from flask import Flask, render_template, request, jsonify
import json
import markdown

app = Flask(__name__)



# Load the text document and tools JSON (for demo purposes, replace with actual file reading)

#
# tools_data = {
# 	"Tool A": ["You should only make one tool call at a time, and if you make a tool call, you should not respond to the user simultaneously. If you respond to the user, you should not make a tool call at the same time.", "You should deny user requests that are against this policy."],
# 	"Tool B": ["You should transfer the user to a human agent if and only if the request cannot be handled within the scope of your actions.ֿֿֿֿֿ", "Each reservation has an reservation id, user id, trip type (one way, round trip), flights, passengers, payment methods, created time, baggages, and travel insurance information."],
# 	"Tool C": ["If the status is", "The agent must first obtain the user id, then ask for the trip type, origin, destination."]
# }


@app.route('/')
def index():
	return render_template('coverage.html', text=policy_text, tools=tools_data)


@app.route('/highlight', methods=['POST'])
def highlight():
	selected_tools = request.json.get("tools", [])
	highlights = set()
	for tool in selected_tools:
		if tool in normalized_passages:
			highlights.update(normalized_passages[tool])

	highlighted_text = policy_text
	for phrase in highlights:
		regex = re.escape(phrase)
		highlighted_text = re.sub(regex, f'<span class="highlight">{phrase}</span>', highlighted_text, flags=re.IGNORECASE)

	return {"highlights": list(highlights), "updated_text": highlighted_text}



if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='parser')
	#parser.add_argument('--policy-path', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/wiki-with-salesforce-policies.md')
	#parser.add_argument('--outdir', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/final with salesforce')
	#parser.add_argument('--policy-path', type=str, default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/wiki-with-policies-for-non-existing-tools.md')
	#parser.add_argument('--outdir', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/final non existing tools')
	parser.add_argument('--policy-path', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/wiki.md')
	#parser.add_argument('--outdir', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/final')
	parser.add_argument('--outdir', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/airline/final copy 4')
	args = parser.parse_args()
	policy_path = args.policy_path
	outdir = args.outdir
	#policy_text = open(policy_path, 'r', encoding='utf-8').read()
	with open(policy_path, 'r', encoding='utf-8') as f:
		policy_text = markdown.markdown(f.read())
		#policy_text = f.read()
	tools_data = defaultdict(list)
	for filename in os.listdir(outdir):
		if filename.endswith(".json"):
			name = filename.replace(".json","")
			print(name)
			with open(os.path.join(outdir,filename),) as f:
				data = json.load(f)
				if isinstance(data["policies"], str):
					continue
				for p in data["policies"]:
					for r in p["references"]:
						tools_data[name].append(r)
	
	
	def normalize_text(text):
		text = text.replace("“", '""').replace("”", '"')
		text = text.replace("\'", '"')
		text = text.replace("‘", "'").replace("’", "'")
		text = text.replace("<p>","")
		text = re.sub(r'\s+', ' ', text).strip()
		return text.lower()
	
	
	# Preprocess tool passages for better search
	normalized_passages = {
		tool: [normalize_text(p) for p in passages]
		for tool, passages in tools_data.items()
	}
					
			
	app.run(debug=True,port=5002)