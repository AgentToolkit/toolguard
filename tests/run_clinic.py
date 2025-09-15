import asyncio
from datetime import datetime
import inspect
import os
import logging
import markdown

#important to load the env variables BEFORE policy_adherence library (so programmatic_ai configuration will take place)
import dotenv
dotenv.load_dotenv() 
import appointment_app.lg_tools as clinic_tools
from toolguard.stages_tptd.text_tool_policy_generator import ToolInfo, step1_main
from toolguard.llm.tg_litellm import LitellmModel
from toolguard.logging_utils import add_log_file_handler
import inspect
import types

logger = logging.getLogger(__name__)

def list_functions_in_module(module):
    return [fn for name, fn in inspect.getmembers(module, inspect.isfunction)]

async def gen_all():
    output_dir = "eval/clinic/output"
    now = datetime.now()
    out_folder = os.path.join(output_dir, now.strftime("%Y-%m-%d_%H_%M_%S"))
    os.makedirs(out_folder, exist_ok=True)
    add_log_file_handler(os.path.join(out_folder, "run.log"))

    
    policy_path = "../ToolGuardAgent/src/appointment_app/clinic_policy_doc.md"
    with open(policy_path, 'r', encoding='utf-8') as f:
        policy_text = markdown.markdown(f.read())

    tools = list_functions_in_module(clinic_tools)

    # Step1
    llm = LitellmModel(model_name='gpt-5-chat-2025-08-07', provider="azure")
    tools_info = [ToolInfo.from_function(fn) for fn in tools]
    step1_out_dir=os.path.join(output_dir, "step1")
    # step1_out_dir = os.path.join(out_folder, "step1")
    # await step1_main(policy_text, tools_info, step1_out_dir, llm, short1=True)

    # Step2
    from toolguard.core import generate_guards_from_tool_policies
    from programmatic_ai.config import settings
    settings.sdk = os.getenv("PROG_AI_PROVIDER") # type: ignore
    return await generate_guards_from_tool_policies(tools,
        from_step1_path=step1_out_dir, 
        to_step2_path=out_folder, 
        # tool_names=["book_reservation"],# "cancel_reservation", "update_reservation_passengers", "update_reservation_baggages", "update_reservation_flights"],
        app_name="clinic"
    )


if __name__ == '__main__':
    from toolguard.logging_utils import init_logging
    init_logging()
    asyncio.run(gen_all())
    logger.info("Done")
