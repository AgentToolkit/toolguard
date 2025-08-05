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
from toolguard.stages_tptd.text_tool_policy_generator import step1_main_with_tools

logger = logging.getLogger(__name__)

def steps1and2(policy_text:str,tools, step1_out_dir:str, step2_out_dir:str, step1_llm:TG_LLM, tools2run:List[str]|None=None, short1=False):
	step1_main_with_tools(policy_text, tools, step1_out_dir,step1_llm, tools2run, short1)
	result = asyncio.run(step2(tools, step1_out_dir, step2_out_dir, tools2run))
	return result


async def step2(funcs:list[Callable], step1_path:str, step2_path:str, app_name:str, tools:Optional[List[str]]=None)->ToolGuardsCodeGenerationResult:
	os.makedirs(step2_path, exist_ok=True)
	add_log_file_handler(os.path.join(step2_path, "run.log"))

	files = [f for f in os.listdir(step1_path) 
		  if os.path.isfile(join(step1_path, f)) and f.endswith(".json")]
	tool_policies = []
	for file in files:
		tool_name = file[:-len(".json")]
		if (not tools) or (tool_name in tools):
			policy = load_tool_policy(join(step1_path, file), tool_name)
			tool_policies.append(policy)
	
	return await generate_toolguards_from_functions(app_name, tool_policies, step2_path, funcs=funcs)
	
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
