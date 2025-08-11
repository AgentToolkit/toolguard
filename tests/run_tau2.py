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
    llm = LitellmModel(model_name='gpt-4o-2024-08-06')
    step1_out_dir = os.path.join(out_folder, "step1")
    doc_summary = lambda doc: doc.strip().split("\n", 1)[1].strip() if "\n" in doc else None
    tools_info = [ToolInfo(
            name=fn.__name__,
            description=doc_summary(inspect.getdoc(fn)) or "",
            parameters=inspect.getdoc(fn)
        ) for fn in funcs]
    # await step1_main(policy_text, tools_info, step1_out_dir, llm, short1=False)

    # Step2
    from toolguard.core import generate_guards_from_tool_policies
    return await generate_guards_from_tool_policies(funcs,
        from_step1_path="eval/airline/GT_tau2/generated_step1_long", 
        to_step2_path=out_folder, 
        # tool_names=["update_reservation_flights"],
        app_name="airline"
    )


if __name__ == '__main__':
    from toolguard.logging_utils import init_logging
    init_logging()
    asyncio.run(gen_all())
    logger.info("Done")
