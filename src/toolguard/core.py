import asyncio
import os
from os.path import join
from typing import Callable, List, Optional

import json
import logging

from toolguard.llm.i_tg_llm import I_TG_LLM
from toolguard.runtime import ToolGuardsCodeGenerationResult
from toolguard.data_types import ToolPolicy, ToolPolicyItem
from toolguard.gen_py.gen_toolguards import generate_toolguards_from_functions, generate_toolguards_from_openapi
from toolguard.tool_policy_extractor.create_oas_summary import OASSummarizer
from toolguard.tool_policy_extractor.text_tool_policy_generator import ToolInfo, extract_policies

logger = logging.getLogger(__name__)

async def build_toolguards(
		policy_text:str, 
		tools: List[Callable]|str, 
		step1_out_dir:str, 
		step2_out_dir:str, 
		step1_llm:I_TG_LLM, 
		app_name:str= "my_app", 
		tools2run: List[str] | None=None, 
		short1=True)->ToolGuardsCodeGenerationResult:
	
	if isinstance(tools, list): #supports list of functions or list of langgraph tools
		tools_info = [ToolInfo.from_function(tool) for tool in tools]
		await extract_policies(policy_text, tools_info, step1_out_dir, step1_llm, tools2run, short1)
		return await generate_guards_from_tool_policies(tools, step1_out_dir, step2_out_dir, app_name, None, tools2run)
	
	if isinstance(tools, str): #Backward compatibility to support OpenAPI specs
		oas_path = tools
		with open(oas_path, 'r', encoding='utf-8') as file:
			oas = json.load(file)
		summarizer = OASSummarizer(oas)
		tools_info = summarizer.summarize()
		await extract_policies(policy_text, tools_info, step1_out_dir, step1_llm, tools2run, short1)
		return await generate_guards_from_tool_policies_oas(oas_path, step1_out_dir, step2_out_dir, app_name, tools2run)
	
	raise "Unknown tools"


async def generate_guards_from_tool_policies(
		funcs: List[Callable],
		from_step1_path: str,
		to_step2_path: str,
		app_name: str,
		lib_names: Optional[List[str]] = None,
		tool_names: Optional[List[str]] = None) -> ToolGuardsCodeGenerationResult:
	os.makedirs(to_step2_path, exist_ok=True)

	tool_policies = load_policies_in_folder(from_step1_path)
	tool_policies = [policy for policy in tool_policies if (not tool_names) or (policy.tool_name in tool_names)]
	return await generate_toolguards_from_functions(app_name, tool_policies, to_step2_path, funcs=funcs, module_roots=lib_names)


async def generate_guards_from_tool_policies_oas(
		oas_path: str,
		from_step1_path: str,
		to_step2_path: str,
		app_name: str,
		tool_names: Optional[List[str]] = None) -> ToolGuardsCodeGenerationResult:
	os.makedirs(to_step2_path, exist_ok=True)
	
	tool_policies = load_policies_in_folder(from_step1_path)
	tool_policies = [policy for policy in tool_policies if (not tool_names) or (policy.tool_name in tool_names)]
	return await generate_toolguards_from_openapi(app_name, tool_policies, to_step2_path, oas_path)


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
