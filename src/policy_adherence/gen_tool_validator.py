import copy
import json
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal

import yaml

from policy_adherence.common.dict import substitute_refs
from policy_adherence.llm.azure_wrapper import AzureLitellm, AzureWrepper
from policy_adherence.llm.llm_model import LLM_model
# from policy_adherence.jschema.json_schema import JSONSchemaModel
from policy_adherence.oas.OAS import OpenAPI, Operation, PathItem, Schema
# from policy_adherence.oas.oas_dom import OASModel
# from policy_adherence.oas.remove_orphan_comps import remove_orphan_components

load_dotenv()

Code = str
class ToolInfo(BaseModel):
    tool_name: str = Field(..., description="Tool name")
    tool_description: str = Field(..., description="Tool description")
    tool_input_schema: Schema = Field(..., description="Tool Input schema")
    tool_output_schema: Schema = Field(..., description="Tool output schema")

class ToolPolicyItem(BaseModel):
    policy: str = Field(..., description="Policy item")
    compliance_examples: Optional[List[str]] = Field(..., description="Case example that complies with the policy")
    violation_examples: Optional[List[str]] = Field(..., description="Case example that violates the policy")

class ToolPolicy(BaseModel):
    tool: ToolInfo
    policy_items: List[ToolPolicyItem]

def fn_is_ok(fn_code, test_cases):
    pass
    # compilation
    # lint
    # hallucinations
    # llm all poliCIES ARE COVERED?
    # llm code that is not described in policy?
    # testcases

def extract_code_from_response(resp:str)->Code:
    start_code_token = "```python\n"
    end_code_token = "```\n\n"
    start = resp.find(start_code_token) + len(start_code_token)
    end = resp.find(end_code_token)
    return resp[start:end]

def generate_signatures(oas: OpenAPI, llm: LLM_model)->Code:
    prompt = f"""Given an OpenAPI Spec, generate Python code that include all the data types as pydantic classes. 
For each operation, create astub function, named by the operationId, with the function description, inputs and outputs.

{oas.model_dump_json(indent=2)}
"""
    msgs = [{"role":"system", "content": prompt}]
    res = llm.chat_json(msgs)
    code = res.choices[0].message.content
    return extract_code_from_response(code)

def generate_validation_fn_code(signatures: Code, policy:ToolPolicy, llm: LLM_model)->Code:
    # test_cases = generate_test_cases(signature, tool_policy.policy_items, llm)
    # try_idx=0, max_try= 5
    valid_fn_code = ""
    # while not fn_is_ok(fn_code, llm) and try_idx< max_try:
    #     valid_fn_code = _generate_validation_fn_code(signature, tool_policy, llm)
    #     try_idx += 1

    return valid_fn_code

def read_oas(file_path:str)->OpenAPI:
    with open(file_path, "r") as file:
        d = yaml.safe_load(file)
    oas = OpenAPI.model_validate(d)
    return oas

def load_policy(file_path:str):
    with open(file_path, "r") as file:
        d = json.load(file)
    policies = d.get("policies", [])
    policy_items = []
    for i, p in enumerate(policies):
        policy_items.append(
            ToolPolicyItem(
                policy = p.get(f"policy description {i+1}"),
                compliance_examples = p.get(f"Compliance Examples {i+1}"),
                violation_examples = p.get(f"Violating Examples {i+1}")
            )
        )
    return policy_items

def op_only_oas(oas: OpenAPI, operationId: str)-> OpenAPI:
    new_oas = OpenAPI(
        openapi=oas.openapi, 
        info=oas.info,
        components=oas.components
    )
    for path, path_item in oas.paths.items():
        for mtd, op in path_item.operations.items():
            if op.operationId == operationId:
                if new_oas.paths.get(path) is None:
                    new_oas.paths[path] = PathItem(
                        summary=path_item.summary,
                        description=path_item.description,
                        servers=path_item.servers,
                        parameters=path_item.parameters,
                    ) # type: ignore
                setattr(
                    new_oas.paths.get(path), 
                    mtd.lower(), 
                    copy.deepcopy(op)
                )
                op = Operation(**(substitute_refs(op.model_dump())))
    return new_oas
    
def main():
    oas_path = "tau_airline/input/openapi.yml"
    tool_names = ["book_reservation"]
    policy_paths = ["tau_airline/input/BookReservation_fix_5.json"]
    model = "gpt-4o-2024-08-06"

    policies = [load_policy(path) for path in policy_paths]
    oas = read_oas(oas_path)
    llm = AzureLitellm(model)

    signatures = generate_signatures(oas, llm)
    for tool_name, tool_poilcy_items in zip(tool_names, policies):
        if len(tool_poilcy_items) == 0: continue
        op_oas = op_only_oas(oas, tool_name)
        op = op_oas.get_operation_by_operationId(tool_name)
        assert op
        tool_info = ToolInfo(
            tool_name=tool_name, 
            tool_description=op.description,
            tool_input_schema=op.requestBody.content_json.schema_,
            tool_output_schema=op.responses.get("200").content_json.schema_
        )
        tool_policy = ToolPolicy(
            tool=tool_info, 
            policy_items=tool_poilcy_items
        )

        code = generate_validation_fn_code(signatures, tool_policy, llm)
        print(code)

if __name__ == '__main__':
    main()