import asyncio
from datetime import datetime
import json
import os
import sys
import yaml
from loguru import logger

#important to load the env variables BEFORE policy_adherence library (so programmatic_ai configuration will take place)
import dotenv
dotenv.load_dotenv() 

from policy_adherence.data_types import ToolPolicy, ToolPolicyItem
from policy_adherence.common.open_api import OpenAPI

model = "gpt-4o-2024-08-06"
# import programmatic_ai
# settings = programmatic_ai.settings
# settings.provider = "azure"
# settings.model = model
# settings.sdk = "litellm"
from policy_adherence.gen_tool_policy_check import generate_tools_check_fns
    
def read_oas(file_path:str)->OpenAPI:
    with open(file_path, "r") as file:
        d = yaml.safe_load(file)
    return OpenAPI.model_validate(d)

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
    return ToolPolicy(name=tool_name, policy_items=items)
    
def symlink_force(target, link_name):
    try:
        os.symlink(target, link_name)
    except FileExistsError:
        os.remove(link_name)
        os.symlink(target, link_name)

async def gen_all():
    oas_path = "/Users/davidboaz/Documents/GitHub/tau_airline/input/openapi.yaml"
    tool_policy_paths = {
        # "cancel_reservation": "/Users/davidboaz/Documents/GitHub/tau_airline/input/CancelReservation.json",
        "book_reservation": "/Users/davidboaz/Documents/GitHub/tau_airline/input/BookReservation.json"
    }
    output_dir = "/Users/davidboaz/Documents/GitHub/tau_airline/output"
    now = datetime.now()
    out_folder = os.path.join(output_dir, now.strftime("%Y-%m-%d_%H_%M_%S"))
    os.makedirs(out_folder, exist_ok=True)

    tool_policies = [load_tool_policy(tool_policy_path, tool_name) 
        for tool_name, tool_policy_path 
        in tool_policy_paths.items()]
    
    result = await generate_tools_check_fns("my_app", tool_policies, out_folder, oas_path)

    print(f"Domain: {result.domain_file}")
    for tool_name, tool in result.tools.items():
        print(f"\t{tool_name}\t{tool.tool_check_file.file_name}")
        for test in tool.test_files:
            print(f"\t{test.file_name}")
    
if __name__ == '__main__':
    logger.remove()
    logger.add(sys.stdout, colorize=True, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> <level>{message}</level>")

    asyncio.run(gen_all())