import asyncio
from datetime import datetime
import os
import sys
from dotenv import load_dotenv
from loguru import logger

from archive.op_only_oas import op_only_oas
from toolguard.common.open_api import read_openapi
from odm.gen_rules import generate_tools_check_rules
from run_gen import load_tool_policy


async def gen_all():
    oas_path = "/Users/davidboaz/Documents/GitHub/tau_airline/input/openapi.yaml"
    tool_policy_paths = {
        "cancel_reservation": "/Users/davidboaz/Documents/GitHub/tau_airline/input/CancelReservation.json",
        "book_reservation": "/Users/davidboaz/Documents/GitHub/tau_airline/input/BookReservation.json"
    }
    output_dir = "/Users/davidboaz/Documents/GitHub/tau_airline/output"
    now = datetime.now()
    out_folder = os.path.join(output_dir, now.strftime("%Y-%m-%d_%H_%M_%S"))
    os.makedirs(out_folder, exist_ok=True)

    oas = read_openapi(oas_path)
    op_oas = op_only_oas(oas, "book_reservation")

    tool_policies = [load_tool_policy(tool_policy_path, tool_name) 
        for tool_name, tool_policy_path 
        in tool_policy_paths.items()]
    
    # domain = OpenAPICodeGenerator(cwd)\
    #     .generate_domain(oas_path, "domain.py")
    result = await generate_tools_check_rules("my_app", tool_policies, out_folder, op_oas)

    # print(f"Domain: {result.domain_file}")
    # for tool_name, tool in result.tools.items():
    #     print(f"\t{tool_name}\t{tool.tool_check_file.file_name}")
    #     for test in tool.test_files:
    #         print(f"\t{test.file_name}")
    
if __name__ == '__main__':
    load_dotenv()
    logger.remove()
    logger.add(sys.stdout, colorize=True, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> <level>{message}</level>")

    asyncio.run(gen_all())