import re
from typing import Any, Dict, Set

from toolguard.buildtime.gen_py import prompts
from toolguard.buildtime.llm.i_tg_llm import I_TG_LLM
from toolguard.runtime.data_types import Domain

MAX_TRIALS = 3


async def tool_dependencies(
    policy_txt: str,
    tool_signature: str,
    domain: Domain,
    llm: I_TG_LLM,
    trial=0,
) -> Set[str]:
    model_options: Dict[str, Any] = {}  # {ModelOption.TEMPERATURE: 0.8}
    pseudo_code = await prompts.tool_policy_pseudo_code(
        llm,
        policy_txt=policy_txt,
        fn_to_analyze=tool_signature,
        data_types=domain.app_types,
        api=domain.app_api,
        model_options=model_options,
    )
    fn_names = _extract_api_calls(pseudo_code)
    if all([f"{fn_name}(" in domain.app_api.content for fn_name in fn_names]):
        return fn_names
    if trial <= MAX_TRIALS:
        # as tool_policy_pseudo_code has some temerature, we retry hoping next time the pseudo code will be correct
        return await tool_dependencies(
            policy_txt, tool_signature, domain, llm, trial + 1
        )
    raise Exception("Failed to analyze api dependencies")


def _extract_api_calls(code: str) -> Set[str]:
    pattern = re.compile(r"\bapi\.(\w+)\s*\(")
    return set(pattern.findall(code))
