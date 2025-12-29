import re

PYTHON_FENCED_PATTERN = r"^```python\s*\n([\s\S]*)\n```"
PYTHON_UNFENCED_PATTERN = r'^python\n([\s\S]*)$'

def get_code_content(llm_code:str) -> str:
    code = llm_code.replace("\\n", "\n")
    
    match = re.match(PYTHON_FENCED_PATTERN, code)
    if match:
        return match.group(1)

    match = re.match(PYTHON_UNFENCED_PATTERN, code)
    if match:
        return match.group(1)

    return code
