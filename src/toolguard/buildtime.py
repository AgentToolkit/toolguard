import os
from os.path import join
from typing import Callable, List, Optional, cast
import json
import logging

from langchain_core.tools import BaseTool


from .llm.i_tg_llm import I_TG_LLM
from .runtime import ToolGuardsCodeGenerationResult
from .data_types import ToolGuardSpec, load_tool_policy, ToolInfo
from .gen_py.gen_toolguards import generate_toolguards_from_functions, generate_toolguards_from_openapi
from .gen_spec.oas_summary import OASSummarizer
from .gen_spec.spec_generator import extract_toolguard_specs
from .common.langchain import langchain_tools_to_openapi

logger = logging.getLogger(__name__)

#Step1 only
async def generate_guard_specs(
	policy_text: str,
    tools: List[Callable] | List[BaseTool] | str,
	llm: I_TG_LLM,
    work_dir: str,
	short = False
)->List[ToolGuardSpec]:
	os.makedirs(work_dir, exist_ok=True)
	
	# case1: path to OpenAPI spec
	oas_path = tools if isinstance(tools, str) else None

	# case2: List of Langchain tools
	if isinstance(tools, list) and all([isinstance(tool, BaseTool) for tool in tools]):
		oas = langchain_tools_to_openapi(tools) # type: ignore
		oas_path = join(work_dir, "oas.json")
		oas.save(oas_path)

	if oas_path: # for cases 1 and 2
		with open(oas_path, 'r', encoding='utf-8') as file:
			oas = json.load(file)
		summarizer = OASSummarizer(oas)
		tools_info = summarizer.summarize()
		return await extract_toolguard_specs(policy_text, tools_info, work_dir, llm, None, short)
	
	# Case 3: List of functions + case 4: List of methods
	if isinstance(tools, list):
		tools_info = [ToolInfo.from_function(tool) for tool in tools]
		return await extract_toolguard_specs(policy_text, tools_info, work_dir, llm, None, short)
	
	raise NotImplementedError()


#Step2 only
async def generate_guards_from_specs(
		tools: List[Callable] | List[BaseTool] | str,
		tool_specs: List[ToolGuardSpec],
		work_dir: str,
		llm: I_TG_LLM,
		app_name: str = "myapp",
		lib_names: Optional[List[str]] = None,
		tool_names: Optional[List[str]] = None) -> ToolGuardsCodeGenerationResult:
	
	tool_specs = [policy for policy in tool_specs if (not tool_names) or (policy.tool_name in tool_names)]
	os.makedirs(work_dir, exist_ok=True)

	# case1: path to OpenAPI spec
	oas_path = tools if isinstance(tools, str) else None

	# case2: List of Langchain tools
	if isinstance(tools, list) and all([isinstance(tool, BaseTool) for tool in tools]):
		oas = langchain_tools_to_openapi(tools) # type: ignore
		oas_path = join(work_dir, "oas.json")
		oas.save(oas_path)

	if oas_path: # for cases 1 and 2
		return await generate_toolguards_from_openapi(app_name, tool_specs, work_dir, oas_path, llm)

	# Case 3: List of functions + case 4: List of methods
	funcs = [cast(Callable, tool) for tool in tools]
	return await generate_toolguards_from_functions(app_name, tool_specs, work_dir, funcs=funcs, llm=llm, module_roots=lib_names)
	

#load step1 results
def load_policies_in_folder(folder:str)->List[ToolGuardSpec]:
	files = [f for f in os.listdir(folder) 
		if os.path.isfile(join(folder, f)) and f.endswith(".json")]
	tool_policies = []
	for file in files:
		tool_name = file[:-len(".json")]
		policy = load_tool_policy(join(folder, file), tool_name)
		if policy.policy_items:
			tool_policies.append(policy)
	return tool_policies


# #Step1 and immediatly step2
# async def build_toolguards(
# 		policy_text:str, 
# 		tools: List[Callable]|str, 
# 		step1_out_dir:str, 
# 		step2_out_dir:str, 
# 		step1_llm:I_TG_LLM,
# 		step2_llm: I_TG_LLM, 
# 		app_name:str= "my_app", 
# 		tools2run: List[str] | None=None, 
# 		short1=True)->ToolGuardsCodeGenerationResult:
	
# 	os.makedirs(step1_out_dir, exist_ok=True)
# 	os.makedirs(step2_out_dir, exist_ok=True)

# 	# case1: path to OpenAPI spec
# 	oas_path = tools if isinstance(tools, str) else None

# 	# case2: List of Langchain tools
# 	if isinstance(tools, list) and all([isinstance(tool, BaseTool) for tool in tools]):
# 		oas = langchain_tools_to_openapi(tools) # type: ignore
# 		oas_path = f"{step1_out_dir}/oas.json"
# 		oas.save(oas_path)

# 	if oas_path: # for cases 1 and 2
# 		with open(oas_path, 'r', encoding='utf-8') as file:
# 			oas = json.load(file)
# 		summarizer = OASSummarizer(oas)
# 		tools_info = summarizer.summarize()
# 		tool_policies = await extract_toolguard_specs(policy_text, tools_info, step1_out_dir, step1_llm, tools2run, short1)
# 		return await generate_guards_from_specs(oas_path, tool_policies, step2_out_dir, llm=step2_llm, app_name=app_name, lib_names=None, tool_names=tools2run)
	
# 	# Case 3: List of functions + case 4: List of methods
# 	if isinstance(tools, list) and not oas_path:
# 		tools_info = [ToolInfo.from_function(tool) for tool in tools]
# 		tool_policies = await extract_toolguard_specs(policy_text, tools_info, step1_out_dir, step1_llm, tools2run, short1)
# 		return await generate_guards_from_specs(tools, tool_policies, step2_out_dir, llm=step2_llm, app_name=app_name, lib_names=None, tool_names=tools2run)
	
# 	raise Exception("Unknown tools")

