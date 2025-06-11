from typing import List

def extract_code_from_llm_response(resp:str)->str:
    start_code_token = "```python\n"
    end_code_token = "```"
    if start_code_token in resp:
        start = resp.find(start_code_token) + len(start_code_token)
        end = resp.rfind(end_code_token)
        return resp[start:end]

    return resp

def post_process_llm_response(resp:str)->str:
    response = extract_code_from_llm_response(resp)
    response = response.replace("\\n", "\n")
    return response

