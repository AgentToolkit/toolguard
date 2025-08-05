import asyncio
from datetime import datetime
import inspect
import os
import logging

#important to load the env variables BEFORE policy_adherence library (so programmatic_ai configuration will take place)
import dotenv
dotenv.load_dotenv() 

from toolguard.logging_utils import add_log_file_handler

logger = logging.getLogger(__name__)

async def gen_all():
    output_dir = "eval/airline/output"
    now = datetime.now()
    out_folder = os.path.join(output_dir, now.strftime("%Y-%m-%d_%H_%M_%S"))
    add_log_file_handler(os.path.join(out_folder, "run.log"))
    
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
    
    # return await generate_toolguards_from_openapi("airline", tool_policies, out_folder, oas_path)
    from toolguard.core import generate_guards_from_tool_policies
    return await generate_guards_from_tool_policies(funcs,
        from_step1_path="eval/airline/GT/airlines", 
        to_step2_path=out_folder, 
        tool_names=["cancel_reservation"],
        app_name="airline"
    )

if __name__ == '__main__':
    from toolguard.logging_utils import init_logging
    init_logging()
    asyncio.run(gen_all())
    logger.info("Done")
