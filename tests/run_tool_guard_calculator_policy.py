import asyncio
from datetime import datetime
import inspect
import os
import logging
import markdown

#important to load the env variables BEFORE policy_adherence library (so programmatic_ai configuration will take place)
import dotenv

from tests.calculator_tools import divide_tool, multiply_tool, add_tool, subtract_tool

dotenv.load_dotenv()

from toolguard.stages_tptd.text_tool_policy_generator import ToolInfo, step1_main
from toolguard.llm.tg_litellm import LitellmModel
from toolguard.logging_utils import add_log_file_handler

logger = logging.getLogger(__name__)

async def gen_all():
	output_dir = "eval/calculator/output"
	now = datetime.now()
	out_folder = os.path.join(output_dir, now.strftime("%Y-%m-%d_%H_%M_%S"))
	os.makedirs(out_folder, exist_ok=True)
	add_log_file_handler(os.path.join(out_folder, "run.log"))

	#from calculator_tools import Calculator
	# policy_path = "eval/airline/wiki.md"
	# with open(policy_path, 'r', encoding='utf-8') as f:
	#     policy_text = markdown.markdown(f.read())
	policy_text = "The calculator must not allow division by zero."
	funcs = [add_tool,subtract_tool,multiply_tool,divide_tool ]  # only @is_tool]

    # Step1
	llm = LitellmModel(model_name='gpt-5-chat-2025-08-07', provider="azure")
	tools_info = [ToolInfo.from_function(tool) for tool in funcs]
	
	step1_out_dir = os.path.join(output_dir, "step1")
	await step1_main(policy_text, tools_info, step1_out_dir, llm, short1=True)

    # Step2
	from toolguard.core import generate_guards_from_tool_policies
	return await generate_guards_from_tool_policies(funcs,from_step1_path=step1_out_dir, to_step2_path=out_folder, app_name="calculator")


if __name__ == '__main__':
    from toolguard.logging_utils import init_logging
    init_logging()
    asyncio.run(gen_all())
    logger.info("Done")
