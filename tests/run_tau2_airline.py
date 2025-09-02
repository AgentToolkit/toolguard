import asyncio
from datetime import datetime
import inspect
import os
import logging
import markdown

#important to load the env variables BEFORE policy_adherence library (so programmatic_ai configuration will take place)
import dotenv
dotenv.load_dotenv() 

from toolguard.stages_tptd.text_tool_policy_generator import ToolInfo, step1_main
from toolguard.llm.tg_litellm import LitellmModel
from toolguard.logging_utils import add_log_file_handler

logger = logging.getLogger(__name__)

async def gen_all():
    output_dir = "eval/airline/output"
    now = datetime.now()
    out_folder = os.path.join(output_dir, now.strftime("%Y-%m-%d_%H_%M_%S"))
    os.makedirs(out_folder, exist_ok=True)
    add_log_file_handler(os.path.join(out_folder, "run.log"))

    from tau2.domains.airline.tools import AirlineTools
    policy_path = "eval/airline/wiki.md"
    with open(policy_path, 'r', encoding='utf-8') as f:
        policy_text = markdown.markdown(f.read())
    funcs = [member for name, member in inspect.getmembers(AirlineTools, predicate=inspect.isfunction)
        if getattr(member, "__tool__", None)]  # only @is_tool]

    # Step1
    llm = LitellmModel(model_name='gpt-5-chat-2025-08-07', provider="azure")
    def doc_summary(doc): 
        paragraphs = [p.strip() for p in doc.split("\n\n") if p.strip()]
        return paragraphs[0] if paragraphs else ""
    tools_info = [ToolInfo.from_function(fn) for fn in funcs]
    step1_out_dir = "eval/airline/tau2/step1_short_gpt5"
    # step1_out_dir = os.path.join(out_folder, "step1")
    # await step1_main(policy_text, tools_info, step1_out_dir, llm, short1=True)

    # Step2
    from toolguard.core import generate_guards_from_tool_policies
    return await generate_guards_from_tool_policies(funcs,
        from_step1_path=step1_out_dir, 
        to_step2_path=out_folder, 
        # tool_names=["book_reservation", "cancel_reservation", "update_reservation_passengers", "update_reservation_baggages", "update_reservation_flights"],
        app_name="airline"
    )


if __name__ == '__main__':
    from toolguard.logging_utils import init_logging
    init_logging()
    asyncio.run(gen_all())
    logger.info("Done")
