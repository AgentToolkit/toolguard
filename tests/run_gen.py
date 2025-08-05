import asyncio
from datetime import datetime
import inspect
import os
import logging

#important to load the env variables BEFORE policy_adherence library (so programmatic_ai configuration will take place)
import dotenv
dotenv.load_dotenv() 

logger = logging.getLogger(__name__)

# from toolguard.__main__ import read_oas_file
# from toolguard.py_to_oas import tools_to_openapi
# from toolguard.stages_tptd.text_policy_identify_process import step1_main


# model = "gpt-4o-2024-08-06"
# import programmatic_ai
# settings = programmatic_ai.settings
# settings.provider = "azure"
# settings.model = model
# settings.sdk = "litellm"
# from toolguard.gen_py.gen_toolguards import generate_toolguards_from_functions, generate_toolguards_from_openapi
    
# from toolguard.common.open_api import OpenAPI
# def read_oas(file_path:str)->OpenAPI:
#     with open(file_path, "r") as file:
#         d = yaml.safe_load(file)
#     return OpenAPI.model_validate(d)

async def gen_all():
    # tool_policy_paths = {
    #     "cancel_reservation": "eval/airline/GT/airlines/CancelReservation.json",
    #     # "book_reservation": "eval/airline/GT/airlines/BookReservation.json",
    #     # "update_reservation_passengers": "eval/airline/GT/airlines/UpdateReservationPassengers.json",
    #     # "update_reservation_flights": "eval/airline/GT/airlines/UpdateReservationFlights.json",
    #     # "update_reservation_baggages": "eval/airline/GT/airlines/UpdateReservationBaggages.json",
    # }
    output_dir = "eval/airline/output"

    # ##Tau1 with wrapper
    # from tau_bench.envs.airline.airline_wrapper import AirlineAPI
    # funcs = [member for name, member in inspect.getmembers(AirlineAPI, predicate=inspect.isfunction)]

    # ##Tau1 with openAPI
    # oas_path = "eval/airline/oas.json"
    # # oas = read_oas(oas_path)

    # Tau2
    from tau2.domains.airline.tools import AirlineTools
    funcs = [member for name, member in inspect.getmembers(AirlineTools, predicate=inspect.isfunction)
        if getattr(member, "__tool__", None)]  # only @is_tool]

    ##Clinic
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
    # os.makedirs(out_folder, exist_ok=True)
    # from toolguard.core import add_log_file_handler
    # add_log_file_handler(os.path.join(out_folder, "run.log"))

    # tool_policies = [load_tool_policy(tool_policy_path, tool_name) 
    #     for tool_name, tool_policy_path 
    #     in tool_policy_paths.items()]
    
    # return await generate_toolguards_from_openapi("airline", tool_policies, out_folder, oas_path)
    from toolguard.core import generate_guards_from_tool_policies
    return await generate_guards_from_tool_policies(funcs,
        from_step1_path="eval/airline/GT/airlines", 
        to_step2_path=out_folder, 
        tool_names=["cancel_reservation"],
        app_name="airline")


if __name__ == '__main__':
    from toolguard.logging_utils import init_logging
    init_logging()
    asyncio.run(gen_all())
    logger.info("Done")
