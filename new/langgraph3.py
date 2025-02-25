import json
import os


import langgraph
from langgraph.graph import StateGraph
from typing import Dict, List, Any, Optional
from langchain.schema import SystemMessage, HumanMessage

from azure_wrapper import AzureWrepper

llm = AzureWrepper()


# State Definition
class TPTDState(Dict[str, Any]):
	policy_text: str
	tools: List[str]
	target_tool: str
	TPTD: Optional[str]
	review_comments: Optional[str]
	iteration: int
	next_step: str


# Creator Node: Generates the TPTD
def creator_node(state: TPTDState) -> TPTDState:
	policy_text = state["policy_text"]
	tools = state["tools"]
	target_tool = state["target_tool"]
	
	prompt = f"""
    You are an AI assistant generating a Tool Policy Text Description (TPTD) for the tool '{target_tool}'.
    Given the policy text:
    {policy_text}
    And the available tools:
    {tools}

    Generate a TPTD containing:
    - A list of policies with descriptions
    - Clarification questions
    - Valid and invalid examples
    """
	
	response = llm.chat([{"role": "system", "content": prompt}])
	state["TPTD"] = response
	state["iteration"] = 0
	return state


# Reviewer Node: Reviews the TPTD
def reviewer_node(state: TPTDState) -> TPTDState:
	tptd = state["TPTD"]
	
	prompt = f"""
    You are an AI assistant reviewing the following TPTD:
    {tptd}

    Generate a list of:
    - Comments for each policy and example
    - Clarification questions
    """
	
	response = llm.chat([{"role": "system", "content": prompt}])

	state["review_comments"] = response
	return state


# Fixer Node: Adjusts the TPTD based on review feedback
def fixer_node(state: TPTDState) -> TPTDState:
	tptd = state["TPTD"]
	review_comments = state.get("review_comments", "")
	
	prompt = f"""
    You are an AI assistant refining the TPTD based on reviewer feedback.

    Original TPTD:
    {tptd}

    Review Comments:
    {review_comments}

    Generate an improved version of the TPTD.
    """
	
	response = llm.chat([{"role": "system", "content": prompt}])
	
	state["TPTD"] = response
	state["iteration"] += 1
	
	# Ensure a valid next step
	if state["iteration"] < 5:
		state["next_step"] = "reviewer"
	else:
		state["next_step"] = "final"
	
	return state


# Define Graph
workflow = StateGraph(TPTDState)
workflow.add_node("creator", creator_node)
workflow.add_node("reviewer", reviewer_node)
workflow.add_node("fixer", fixer_node)
workflow.add_node("final", lambda state: state)  # Final step as a passthrough

# Define Edges
workflow.add_edge("creator", "reviewer")
workflow.add_edge("reviewer", "fixer")
workflow.add_conditional_edges("fixer", lambda state: state["next_step"], {"reviewer": "reviewer", "final": "final"})

# Define Entry Point
workflow.set_entry_point("creator")

# Compile Graph
executor = workflow.compile()



dir = "/Users/naamazwerdling/workspace/tau-bench/tau_bench/envs/airline/tools"
data_dir = "/Users/naamazwerdling/workspace/tau-bench/tau_bench/envs/airline/data"
policy_path = "/Users/naamazwerdling/workspace/tau-bench/tau_bench/envs/airline/wiki.md"
outdir = "/Users/naamazwerdling/Documents/OASB/policy_validation/lc/tau_airline_res/"
functions_schema = "/Users/naamazwerdling/Documents/OASB/policy_validation/tau_airline_res/fc_schema.json"
policy_text = open(policy_path, 'r').read()
outfile = os.path.join(outdir, "fc_schema.json")
with open(outfile, 'r') as file:
	functions =  json.load(file)

fsummary = {}
for k, v in functions.items():
	fsummary[k] = v['description']

for function_name, function_data in functions.items():
	fname = function_data["name"]
	# Example Input
	input_state = {
		"policy_text": policy_text,
		"tools": fsummary,
		"target_tool": fname
	}
	
	# Run Workflow
	final_output = executor.invoke(input_state)
	print(final_output)
