from typing import List

def extract_code_from_llm_response(resp:str)->str:
    start_code_token = "```python\n"
    end_code_token = "```"
    start = resp.find(start_code_token) + len(start_code_token)
    end = resp.rfind(end_code_token)
    return resp[start:end]


def to_md_bulltets(items: List[str])->str:
    s = ""
    for item in items:
        s+=f"* {item}\n"
    return s
