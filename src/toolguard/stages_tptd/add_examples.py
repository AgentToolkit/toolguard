import argparse
import json
import os
from typing import List, Dict, Optional
import markdown
from langgraph.graph import StateGraph
from toolguard.stages_tptd.create_oas_summary import OASSummarizer
import dotenv

from toolguard.stages_tptd.text_policy_identify_process import PolicyIdentifier
from toolguard.stages_tptd.utils import TPTDState

dotenv.load_dotenv()


class AddExamples(object):
	def __init__(self,model:str='gpt-4o-2024-08-06'):
		pi = PolicyIdentifier(model)
		workflow = StateGraph(TPTDState)
		
		workflow.add_node("example_creator", pi.example_creator)
		workflow.add_node("add_examples",pi.add_examples)
		workflow.add_node("merge_examples", pi.merge_examples)
		workflow.add_node("fix_examples",pi.fix_examples)
		workflow.add_node("review_examples", pi.review_examples)
		workflow.add_node("final", lambda state: state)
		
		workflow.set_entry_point("example_creator")
		workflow.add_edge("example_creator", "add_examples")
		workflow.add_conditional_edges("add_examples",lambda state: "merge_examples" if state.get("stop", False) else "add_examples")
		# workflow.add_edge("merge_examples", "fix_examples")
		# workflow.add_edge("fix_examples","review_examples")
		workflow.add_edge("merge_examples", "review_examples")
		workflow.add_edge("review_examples", "final")
		
		self.executor = workflow.compile()
		
		
		
		
	
	
	

def step1_add_examples_main(policy_text:str, oas:Dict, step1_output_dir:str,model,tptd_dir:str, tools:Optional[List[str]]=None):
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
			tptd_file_name = os.path.join(tptd_dir, fname+'.json')
			tptd = json.load(open(tptd_file_name))
			input_state = {
				"policy_text": policy_text,
				"tools": fsummary,
				"target_tool": fname,
				"target_tool_description": detail,
				"outdir": process_dir,
				"TPTD":tptd
			}
			p2 = AddExamples(model)
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
	domain = "library"
	parser.add_argument('--model-name', type=str,default='gpt-4o-2024-08-06')
	parser.add_argument('--policy-path', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/orca/empty.txt')
	parser.add_argument('--oas', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/orca/'+domain+'/oas.json')
	parser.add_argument('--tptd-dir', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/orca/'+domain+'/s1_just_policies')
	parser.add_argument('--outdir', type=str,default='/Users/naamazwerdling/Documents/OASB/policy_validation/orca/'+domain+'/step1')
	parser.add_argument('--tools', nargs='+', default=None, help='Optional list of tool names. These are a subset of the tools in the openAPI operation ids.')

	args = parser.parse_args()
	policy_path = args.policy_path
	oas_file = args.oas
	outdir = args.outdir
	
	policy_text = open(policy_path, 'r',encoding='utf-8').read()
	policy_text = markdown.markdown(policy_text)

	with open(oas_file,'r',encoding='utf-8') as file:
		oas = json.load(file)
	
	

		
	step1_add_examples_main(policy_text,oas,outdir,args.model_name,args.tptd_dir,args.tools)
	

