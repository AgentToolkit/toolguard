from datetime import datetime
import json
import os
import sys
import yaml
from typing import List
from dotenv import load_dotenv
from loguru import logger

from policy_adherence.types import SourceFile, ToolPolicy, ToolPolicyItem
from policy_adherence.gen_domain import OpenAPICodeGenerator
from policy_adherence.llm.azure_wrapper import AzureLitellm
from policy_adherence.common.open_api import OpenAPI

model = "gpt-4o-2024-08-06"
# import programmatic_ai
# settings = programmatic_ai.settings
# settings.provider = "azure"
# settings.model = model
# settings.sdk = "litellm"
from policy_adherence.gen_tool_policy_check import PolicyAdherenceCodeGenerator
    
def read_oas(file_path:str)->OpenAPI:
    with open(file_path, "r") as file:
        d = yaml.safe_load(file)
    return OpenAPI.model_validate(d)

def load_policy(file_path:str, tool_name:str)->ToolPolicy:
    with open(file_path, "r") as file:
        d = json.load(file)
    
    policies = d.get("policies", [])
    policy_items = []
    for i, p in enumerate(policies):
        policy_items.append(
            ToolPolicyItem(
                policy = p.get(f"policy description {i+1}"),
                compliance_examples = p.get(f"Compliance Examples {i+1}"),
                violation_examples = p.get(f"Violating Examples {i+1}")
            )
        )
    return ToolPolicy(name=tool_name, policy_items=policy_items)

# def op_only_oas(oas: OpenAPI, operationId: str)-> OpenAPI:
#     new_oas = OpenAPI(
#         openapi=oas.openapi, 
#         info=oas.info,
#         components=oas.components
#     )
#     for path, path_item in oas.paths.items():
#         for mtd, op in path_item.operations.items():
#             if op.operationId == operationId:
#                 if new_oas.paths.get(path) is None:
#                     new_oas.paths[path] = PathItem(
#                         summary=path_item.summary,
#                         description=path_item.description,
#                         servers=path_item.servers,
#                         parameters=path_item.parameters,
#                     ) # type: ignore
#                 setattr(
#                     new_oas.paths.get(path), 
#                     mtd.lower(), 
#                     copy.deepcopy(op)
#                 )
#                 op = Operation(**(substitute_refs(op.model_dump())))
#     return new_oas
    
def symlink_force(target, link_name):
    try:
        os.symlink(target, link_name)
    except FileExistsError:
        os.remove(link_name)
        os.symlink(target, link_name)

def main():
    oas_path = "tau_airline/input/openapi.yaml"
    tool_names = ["book_reservation"]
    policy_paths = ["tau_airline/input/BookReservation_fix_5.json"]
    output_dir = "tau_airline/output"
    now = datetime.now()
    cwd = os.path.join(output_dir, now.strftime("%Y-%m-%d %H:%M:%S"))
    os.makedirs(cwd, exist_ok=True)

    tool_policies = [load_policy(path,tool_name) 
        for tool_name, path 
        in zip(tool_names, policy_paths)]
    llm = AzureLitellm(model)
    
    domain = OpenAPICodeGenerator(cwd)\
        .generate_domain(oas_path, "domain.py")
    result = PolicyAdherenceCodeGenerator(llm, cwd)\
        .generate_tools_check_fns(tool_policies, domain)

    print(f"Domain: {result.domain_file}")
    for tool_name, tool in result.tools.items():
        print(f"\t{tool_name}\t{tool.check_file_name}\t{tool.tests_file_name}")
    

if __name__ == '__main__':
    load_dotenv()
    logger.remove()
    logger.add(sys.stdout, colorize=True, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> <level>{message}</level>")

    main()