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
    output_dir = "eval/telecom/output"
    now = datetime.now()
    out_folder = os.path.join(output_dir, now.strftime("%Y-%m-%d_%H_%M_%S"))
    os.makedirs(out_folder, exist_ok=True)
    add_log_file_handler(os.path.join(out_folder, "run.log"))

    from tau2.domains.telecom.tools import TelecomTools
    from tau2.domains.telecom.utils import TELECOM_MAIN_POLICY_PATH, TELECOM_TECH_SUPPORT_POLICY_MANUAL_PATH
    from tau2.utils import load_file

    main_policy = load_file(TELECOM_MAIN_POLICY_PATH)
    tech_support_policy = load_file(TELECOM_TECH_SUPPORT_POLICY_MANUAL_PATH)
    policy_text = f"""<main_policy>
    {main_policy}
    </main_policy>
    <tech_support_policy>\
    {tech_support_policy}
    </tech_support_policy>
    """
    
    funcs = [member for name, member in inspect.getmembers(TelecomTools, predicate=inspect.isfunction)
        if getattr(member, "__tool__", None)]  # only @is_tool]

    # Step1
    llm = LitellmModel(model_name='gpt-4o-2024-08-06')
    def doc_summary(doc): 
        paragraphs = [p.strip() for p in doc.split("\n\n") if p.strip()]
        return paragraphs[0] if paragraphs else ""
    tools_info = [ToolInfo(
            name=fn.__name__,
            description=doc_summary(inspect.getdoc(fn)) or "",
            parameters=inspect.getdoc(fn)
        ) for fn in funcs]
    step1_out_dir = os.path.join(out_folder, "step1")
    await step1_main(policy_text, tools_info, step1_out_dir, llm, short1=False, tools_shortlist=["resume_line"])

    return
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
