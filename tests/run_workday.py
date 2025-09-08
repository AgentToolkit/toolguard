import asyncio
from datetime import datetime
import inspect
import os
import logging
import markdown

#important to load the env variables BEFORE policy_adherence library (so programmatic_ai configuration will take place)
import dotenv
from ibm_watsonx_orchestrate.agent_builder.tools import PythonTool

dotenv.load_dotenv()

from toolguard.stages_tptd.text_tool_policy_generator import ToolInfo, step1_main
from toolguard.llm.tg_litellm import LitellmModel
from toolguard.logging_utils import add_log_file_handler

logger = logging.getLogger(__name__)


async def gen_all():
    output_dir = "eval/workday/output"
    now = datetime.now()
    out_folder = os.path.join(output_dir, now.strftime("%Y-%m-%d_%H_%M_%S"))
    os.makedirs(out_folder, exist_ok=True)
    add_log_file_handler(os.path.join(out_folder, "run.log"))

    import workday.tools_list
    from workday.tools_list import functions

    policy_path = "eval/workday/wiki.md"
    with open(policy_path, 'r', encoding='utf-8') as f:
        policy_text = markdown.markdown(f.read())

    # todo: use unwrap_fn for pythontool (uncomment @tool(s))

    # # step1
    # llm = LitellmModel(model_name='gpt-4o-2024-08-06', provider = "azure")
    #
    # def doc_summary(doc, fn):
    #     paragraphs = [p.strip() for p in doc.split("\n\n") if p.strip()]
    #     return paragraphs[0] if paragraphs else ""
    #
    # tools_info = [ToolInfo(
    #         name=fn.__name__ if not isinstance(fn, PythonTool) else fn.name,
    #         description=doc_summary(inspect.getdoc(fn), fn) or "",
    #         parameters=inspect.getdoc(fn)
    #     ) for fn in functions]

    step1_out_dir = "eval/workday/step1_short"
    ## step1_out_dir = os.path.join(out_folder, "step1")
    # await step1_main(policy_text, tools_info, step1_out_dir, llm, short1=True)

    # step2
    from toolguard.core import generate_guards_from_tool_policies
    return await generate_guards_from_tool_policies(functions,
        from_step1_path=step1_out_dir,
        to_step2_path=out_folder,
        lib_names=['workday', 'agent_ready_tools'],
        #tool_names=["book_reservation", "cancel_reservation", "update_reservation_passengers",
        #            "update_reservation_baggages", "update_reservation_flights"],
        app_name="wd"
    )


from programmatic_ai.config import settings
settings.sdk = os.getenv("PROG_AI_PROVIDER")  # type: ignore


if __name__ == '__main__':
    from toolguard.logging_utils import init_logging
    init_logging()
    asyncio.run(gen_all())
    logger.info("Done")
