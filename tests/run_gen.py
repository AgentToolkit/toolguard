import asyncio
from datetime import datetime
import inspect
import json
import os
import sys
import markdown
import yaml
from loguru import logger

#important to load the env variables BEFORE policy_adherence library (so programmatic_ai configuration will take place)
import dotenv

dotenv.load_dotenv() 

# from toolguard.__main__ import read_oas_file
# from toolguard.py_to_oas import tools_to_openapi
# from toolguard.stages_tptd.text_policy_identify_process import step1_main

from tau_bench.envs.airline.airline_wrapper import ALL_TOOLS
from toolguard.data_types import ToolPolicy, ToolPolicyItem
from toolguard.common.open_api import OpenAPI

# model = "gpt-4o-2024-08-06"
# import programmatic_ai
# settings = programmatic_ai.settings
# settings.provider = "azure"
# settings.model = model
# settings.sdk = "litellm"
from toolguard.gen_py.gen_toolguards import generate_toolguards_from_functions
    
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
    return ToolPolicy(tool_name=tool_name, policy_items=items)
    
# def symlink_force(target, link_name):
#     try:
#         os.symlink(target, link_name)
#     except FileExistsError:
#         os.remove(link_name)
#         os.symlink(target, link_name)

async def gen_all():
    tool_policy_paths = {
        "cancel_reservation": "eval/airline/GT/airlines-examples-verified/CancelReservation-verified.json",
        "book_reservation": "eval/airline/GT/airlines-examples-verified/BookReservation-verified.json",
        "update_reservation_passengers": "eval/airline/GT/airlines-examples-verified/UpdateReservationPassengers-verified.json",
        "update_reservation_flights": "eval/airline/GT/airlines-examples-verified/UpdateReservationFlights-verified.json",
        "update_reservation_baggages": "eval/airline/GT/airlines-examples-verified/UpdateReservationBaggages-verified.json",
    }
    output_dir = "eval/airline/output"
    # from tau2.domains.airline.tools import AirlineTools
    # funcs = [member for name, member in inspect.getmembers(AirlineTools, predicate=inspect.isfunction)
    #     if getattr(member, "__tool__", None)]  # only @is_tool]

    from tau_bench.envs.airline.airline_wrapper import AirlineAPI
    funcs = [member for name, member in inspect.getmembers(AirlineAPI, predicate=inspect.isfunction)]

    # from tau_bench.envs.airline.tools import ALL_TOOLS
    # funcs = ALL_TOOLS

    oas_path = "eval/airline/oas.json"
    oas = read_oas(oas_path)
    # policy_path = "../ToolGuardAgent/eval/clinic/clinic_policy_doc.md"
    # with open(policy_path, 'r', encoding='utf-8') as f:
    #     policy_text = markdown.markdown(f.read())

    # from appointment_app.lg_tools import add_user, add_payment_method, get_user_payment_methods
    # output_dir = "eval/clinic/output"
    # funcs = [add_user, add_payment_method, get_user_payment_methods]
    # # oas = tools_to_openapi("Clinic", [add_user])
    # # oas.save(oas_path)
    # # step1_main(policy_text, read_oas_file(oas_path), output_dir, 'gpt-4o-2024-08-06', tools=["add_user"])
    # tool_policy_paths = {
    #     "add_user": "../ToolGuardAgent/eval/clinic/output/add_user.json"
    # }

    now = datetime.now()
    out_folder = os.path.join(output_dir, now.strftime("%Y-%m-%d_%H_%M_%S"))
    os.makedirs(out_folder, exist_ok=True)
    logger.add(
        os.path.join(out_folder, "run.log"),     # Log file path
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        encoding="utf-8"
    )
    logger.info("ASasas")

    tool_policies = [load_tool_policy(tool_policy_path, tool_name) 
        for tool_name, tool_policy_path 
        in tool_policy_paths.items()]
    
    return await generate_toolguards_from_functions("airline", tool_policies, out_folder, funcs, ["tau_bench"])

    # out_folder = "eval/airline/output/last"
    # result = load(out_folder)
    # print(result.model_dump_json(indent=2, exclude_none=True, by_alias=True))

    # result.check_tool_call("add_user", {
    #         "first_name": "A", 
    #         "last_name": "B:",
    #         "address": "aasa",
    #     },
    #     [])
    
if __name__ == '__main__':
    logger.remove()
    #  Console logging
    logger.add(
        sys.stdout, 
        colorize=True, 
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> <level>{message}</level>"
    )

    asyncio.run(gen_all())
    print("Done")
