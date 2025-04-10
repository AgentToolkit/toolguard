import asyncio
from datetime import datetime
import json
import os
import sys
import yaml
from typing import List
from dotenv import load_dotenv
from loguru import logger

from policy_adherence.types import SourceFile, ToolPolicy, ToolPolicyItem
from policy_adherence.common.open_api import OpenAPI

model = "gpt-4o-2024-08-06"
# import programmatic_ai
# settings = programmatic_ai.settings
# settings.provider = "azure"
# settings.model = model
# settings.sdk = "litellm"
from policy_adherence.gen_tool_policy_check import ToolCheckPolicyGenerator, check_fn_module_name, generate_tools_check_fns, test_fn_module_name
    
def read_oas(file_path:str)->OpenAPI:
    with open(file_path, "r") as file:
        d = yaml.safe_load(file)
    return OpenAPI.model_validate(d)

def load_policy_new(file_path:str, tool_name:str)->ToolPolicy:
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
    return ToolPolicy(name=tool_name, policy_items=items)
    
def symlink_force(target, link_name):
    try:
        os.symlink(target, link_name)
    except FileExistsError:
        os.remove(link_name)
        os.symlink(target, link_name)

async def gen_all():
    oas_path = "/Users/davidboaz/Documents/GitHub/tau_airline/input/openapi.yaml"
    tool_names = [
        "cancel_reservation",
        "book_reservation"
    ]
    policy_paths = [
        "/Users/davidboaz/Documents/GitHub/tau_airline/input/CancelReservation.json"
        # "/Users/davidboaz/Documents/GitHub/tau_airline/input/BookReservation.json"
    ]
    output_dir = "/Users/davidboaz/Documents/GitHub/tau_airline/output"
    now = datetime.now()
    out_folder = os.path.join(output_dir, now.strftime("%Y-%m-%d_%H_%M_%S"))
    os.makedirs(out_folder, exist_ok=True)

    tool_policies = [load_policy_new(path, tool_name) 
        for tool_name, path 
        in zip(tool_names, policy_paths)]
    
    # domain = OpenAPICodeGenerator(cwd)\
    #     .generate_domain(oas_path, "domain.py")
    result = await generate_tools_check_fns("my_app", tool_policies, out_folder, oas_path)

    print(f"Domain: {result.domain_file}")
    for tool_name, tool in result.tools.items():
        print(f"\t{tool_name}\t{tool.tool_check_file.file_name}")
        for test in tool.test_files:
            print(f"\t{test.file_name}")
    

async def gen_tool_check_fn(case:str):
    cwd = f"tau_airline/output/{case}"
    tool_name = "book_reservation"
    policy_path = "tau_airline/input/BookReservation.json"
    tool = load_policy_new(policy_path, tool_name)
    item = tool.policy_items[0]
    # domain = SourceFile.load_from(os.path.join(cwd, "domain.py"))
    # check_fn = SourceFile.load_from(os.path.join(cwd, "check_book_reservation.py"))
    # tests = [
    #     SourceFile.load_from(os.path.join(cwd, "test_check_Baggage Allowance.py")),
    #     SourceFile.load_from(os.path.join(cwd, "test_check_Passenger Information.py")),
    #     SourceFile.load_from(os.path.join(cwd, "test_check_Payment Method Restrictions.py")),
    # ]
    gen = ToolCheckPolicyGenerator(tool, cwd)
    items = [item]
    check_futures = [
        gen.improve_tool_item_check_fn_loop(tool_item, check_fn, test)
        for tool_item in items 
    ]
    checks = await asyncio.gather(*check_futures)
    # res = await gen._generate_tool_check_fn(domain, check_fn, tool, test)
    print(checks)

if __name__ == '__main__':
    load_dotenv()
    logger.remove()
    logger.add(sys.stdout, colorize=True, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> <level>{message}</level>")

    asyncio.run(gen_all())
    # asyncio.run(gen_tool_check_fn("game"))