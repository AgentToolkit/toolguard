import re
from typing import Set
from toolguard.data_types import Domain, ToolPolicyItem
from toolguard.gen_py.prompts.pseudo_code import tool_policy_pseudo_code

MAX_TRIALS = 3
async def tool_dependencies(policy_item: ToolPolicyItem, tool_signature: str, domain:Domain, trial=0) -> Set[str]:
    pseudo_code = await tool_policy_pseudo_code(policy_item, tool_signature, domain)
    fn_names = _extract_api_calls(pseudo_code)
    if all([f"{fn_name}(" in domain.app_api.content for fn_name in fn_names]):
        return fn_names
    if trial<=MAX_TRIALS:
        return await tool_dependencies(policy_item, tool_signature, domain, trial+1)
    raise Exception("Failed to analyze api dependencies")


def _extract_api_calls(code: str) -> Set[str]:
    pattern = re.compile(r'\bapi\.(\w+)\s*\(')
    return set(pattern.findall(code))