import asyncio
import os
from os.path import join
from typing import Callable, List, Optional

import json
import logging

from toolguard.llm.tg_llm import TG_LLM
from toolguard.logging_utils import add_log_file_handler
from toolguard.runtime import ToolGuardsCodeGenerationResult
from toolguard.data_types import ToolPolicy, ToolPolicyItem
from toolguard.gen_py.gen_toolguards import generate_toolguards_from_functions
from toolguard.stages_tptd.text_tool_policy_generator import ToolInfo, step1_main

logger = logging.getLogger(__name__)

async def build_toolguards(policy_text:str, tools: List[Callable], out_dir:str, step1_llm:TG_LLM, app_name:str="my_app", tools2run:List[str]|None=None, short1=False):
	os.makedirs(out_dir, exist_ok=True)
	step1_out_dir = join(out_dir, "step1")
	step2_out_dir = join(out_dir, "step2")

	tools_info = functions_to_tool_info(tools)
	await step1_main(policy_text, tools_info, step1_out_dir,step1_llm, tools2run, short1)
	result = await generate_guards_from_tool_policies(tools, step1_out_dir, step2_out_dir, app_name, tools2run)
	return result

def functions_to_tool_info(funcs: List[Callable])->List[ToolInfo]:
	#Assumes @tool decorator from langchain https://python.langchain.com/docs/how_to/custom_tools/ 
	# or a plain function with doc string
	return [ToolInfo(
				name=func.name if hasattr(func, 'name') else func.__name__,
				description= func.description if hasattr(func, 'description') else func.__doc__.strip() if func.__doc__ else "",
				parameters=func.args_schema.model_json_schema() if hasattr(func, 'args_schema') else {}
			) for func in funcs]

async def generate_guards_from_tool_policies(
		funcs: List[Callable],
		from_step1_path: str,
		to_step2_path: str,
		app_name: str,
		tool_names: Optional[List[str]] = None) -> ToolGuardsCodeGenerationResult:
	os.makedirs(to_step2_path, exist_ok=True)

	tool_policies = load_policies_in_folder(from_step1_path)
	tool_policies = [policy for policy in tool_policies if (not tool_names) or (policy.tool_name in tool_names)]
	return await generate_toolguards_from_functions(app_name, tool_policies, to_step2_path, funcs=funcs)
	
def load_policies_in_folder(folder:str, ):
	files = [f for f in os.listdir(folder) 
		if os.path.isfile(join(folder, f)) and f.endswith(".json")]
	tool_policies = []
	for file in files:
		tool_name = file[:-len(".json")]
		policy = load_tool_policy(join(folder, file), tool_name)
		if policy.policy_items:
			tool_policies.append(policy)
	return tool_policies

def load_tool_policy(file_path:str, tool_name:str)->ToolPolicy:
    with open(file_path, "r") as file:
        d = json.load(file)
    
    items = [ToolPolicyItem(
                name=item.get("policy_name"),
                description = item.get("description"),
                references = item.get("references"),
                compliance_examples = item.get("compliance_examples"),
                violation_examples = item.get("violating_examples")
            )
            for item in d.get("policies", [])
            if not item.get("skip")]
    return ToolPolicy(tool_name=tool_name, policy_items=items)
