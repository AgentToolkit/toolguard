import ast
import astor
import copy
from datetime import datetime
import json
import os
import sys
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Tuple

from policy_adherence.code import Code
from policy_adherence.common.array import find
from policy_adherence.common.dict import substitute_refs
from policy_adherence.llm.azure_wrapper import AzureLitellm
from policy_adherence.llm.llm_model import LLM_model
from policy_adherence.oas import OpenAPI, Operation, PathItem
from policy_adherence.unittests import run_unittests
from loguru import logger
    
logger.remove()
logger.add(sys.stdout, colorize=True, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> <level>{message}</level>")

class ToolPolicyItem(BaseModel):
    policy: str = Field(..., description="Policy item")
    compliance_examples: Optional[List[str]] = Field(..., description="Case example that complies with the policy")
    violation_examples: Optional[List[str]] = Field(..., description="Case example that violates the policy")
class ToolInfo(BaseModel):
    tool_name: str = Field(..., description="Tool name")
    tool_description: str = Field(..., description="Tool description")
    policy_items: List[ToolPolicyItem]


def fn_is_ok(fn_code: Code, domain: Code, test_cases:Code, llm: LLM_model, output_path:str):
    report = run_unittests(output_path)
    return all([test.outcome == "passed" for test in report.tests])
    # lint
    # hallucinations
    # llm all poliCIES ARE COVERED?
    # llm code that is not described in policy?
    return True

def extract_code_from_response(resp:str)->str:
    start_code_token = "```python\n"
    end_code_token = "```"
    start = resp.find(start_code_token) + len(start_code_token)
    end = resp.rfind(end_code_token)
    return resp[start:end]

def generate_domain(oas: OpenAPI, llm: LLM_model, retries=2)->Code:
    logger.debug(f"Generating domain... (retry = {retries})")
    prompt = f"""Given an OpenAPI Spec, generate Python code that include all the data types as pydantic classes. 
For data-classes, make all fields optional.
For each operation, create a function stub.
The function name comes from the operation operationId.
The function argument names and types come from the operation parameters and requestBody.
The function return-type comes from the operation 200 response.
Add the operation description as the function documentation.

{oas.model_dump_json(indent=2)}
"""
    msgs = [{"role":"system", "content": prompt}]
    res = llm.chat_json(msgs)
    res_content = res.choices[0].message.content
    code = extract_code_from_response(res_content)

    try:
        ast.parse(code) #check syntax
        return Code(file_name="domain.py", content=code)
    except Exception as ex:
        logger.warning(f"Generated domain have invalid syntax. {str(ex)}")
        if retries>1:
            return generate_domain(oas, llm, retries=retries-1) #retry
        raise ex

def policy_statements(tool: ToolInfo):
    s = ""
    for i, item in enumerate(tool.policy_items):
        s+= f"## Policy item {i+1}"
        s+=f"{item.policy}\n"
        if item.compliance_examples:
            s+="### Positive examples\n"
            for pos_ex in item.compliance_examples:
                s+=f"* {pos_ex}\n"
        if item.violation_examples:
            s+="### Negative examples\n"
            for neg_ex in item.violation_examples:
                s+=f"* {neg_ex}\n"
        s+="\n"
    return s

def function_stub(domain:Code, fn_name:str, new_fn_name:str)->Optional[str]:
    tree = ast.parse(domain.content)
    new_body = []
    new_body.append(ast.ImportFrom(
        module=domain.file_name[:-3],# The module name (without ./)
        names=[ast.alias(name="*", asname=None)],  # Import Type
        level=0            # 0 = absolute import, 1 = relative import (.)
    ))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == fn_name:
            node.name = new_fn_name
            node.returns = ast.Constant(value=None)
            node.body = [ast.Pass()]
            new_body.append(node)
    
    module = ast.Module(body=new_body, type_ignores=[])
    ast.fix_missing_locations(module)
    return astor.to_source(module)

def generate_test_cases(fn_under_test:Code, tool: ToolInfo, llm: LLM_model, retries=2)-> Code:
    logger.debug(f"Generating Tests... (retries={retries})")
    prompt = f"""You are given a function stub in Python. This function is under test:
```
### {fn_under_test.file_name}
{fn_under_test.content}
```
make sure to import it from {fn_under_test.file_name}.

You are also given with policy statements that the function under test should comply with.
For each statement, you are also provided with positive and negative examples.

Your task is to write unit tests to check that the function implementation check the policy statements.
Generate one test for each policy statement example.
For negative examples, check that the funtion under test raise a `builtins.Exception`.
For positive cases check that no exception raised.
Indicate test failures using a meaningful message that also contain the policy statement and the example.

{policy_statements(tool)}
"""
    msgs = [{"role":"system", "content": prompt}]
    res = llm.chat_json(msgs)
    res_content = res.choices[0].message.content
    code = extract_code_from_response(res_content)
    
    try:
        ast.parse(code)
        return Code(file_name=f"test_check_{tool.tool_name}.py", content=code)
    except Exception as ex:
        logger.warning(f"Generated tests have invalid syntax. {str(ex)}")
        if retries>0:
            return generate_test_cases(fn_under_test, tool, llm, retries=retries-1)
        raise ex

def generate_validation_fn_code_draft(domain: Code, tool_info:ToolInfo)->Code:
    tool_name = tool_info.tool_name
    check_fn_name = f"check_{tool_name}"
    fn_code = function_stub(domain, tool_name, check_fn_name)
    assert fn_code
    return Code(file_name=f"{check_fn_name}.py", content=fn_code)

def generate_validation_fn_code(domain: Code, tool_info:ToolInfo, llm: LLM_model, retries=2)->Code:
    logger.debug(f"Generated function... (retry = {retries})")
    tool_name = tool_info.tool_name
    check_fn_name = f"check_{tool_name}"
    fn_signature = function_stub(domain, tool_name, check_fn_name)
    prompt = f"""You are given a function signature:
```
### {check_fn_name}.py
{fn_signature}
```
You are given domain with data classes and functions.
You are also given with a list of policy items. Policy items have a list of positive and negative examples. 

Implement the function `{check_fn_name}()`.
The function implementation should check that all the policy items hold. 
In particular, it should support the positive examples, and raise meaningful exception in the negative examples.
If you need to retrieve additional data (that is not in the function arguments), you can call functions defined in the domain.
```
### domain.file_name
{domain.content}
```

# Policy Items:
{policy_statements(tool_info)}
"""
    msgs = [{"role":"system", "content": prompt}]
    res = llm.chat_json(msgs)
    res_content = res.choices[0].message.content
    code = extract_code_from_response(res_content)

    try:
        ast.parse(code)
        return Code(file_name=f"{check_fn_name}.py", content=code)
    except Exception as ex:
        logger.warning(f"Generated function failed. Syntax error. {str(ex)}")
        if retries>0:
            return generate_validation_fn_code(domain, tool_info, llm, retries-1)
        raise ex

def generate_function(domain: Code, tool_info:ToolInfo, llm: LLM_model, output_path:str, retries=3)->Tuple[Code, Code]:
    valid_fn_code = generate_validation_fn_code_draft(domain, tool_info)
    valid_fn_code.save(output_path)
    logger.debug(f"Tool {tool_info.tool_name} function draft created")

    tests = generate_test_cases(valid_fn_code, tool_info, llm)
    tests.save(output_path)
    report = run_unittests(output_path) #still running against a stub. the tests should fail, but the collector should not fail.
    if not all([col.outcome == "passed" for col in report.collectors]):
        logger.debug(f"Tool {tool_info.tool_name} unit tests error")
        # TODO retry
    logger.debug(f"Tool {tool_info.tool_name} unit tests created")

    valid_fn = lambda: fn_is_ok(valid_fn_code, domain, tests, llm, output_path)
    logger.debug(f"Tool {tool_info.tool_name} function is {'valid' if valid_fn() else 'invalid'}")
    while retries > 0 and not valid_fn():
        logger.debug(f"Tool {tool_info.tool_name} function is invalid. Retrying...")
        valid_fn_code = generate_validation_fn_code(domain, tool_info, llm)
        retries -=1

    return valid_fn_code, tests

def load_domain(file_path:str)->Code:
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
    return Code(
        file_name=os.path.basename(file_path),
        content=content
    )

def read_oas(file_path:str)->OpenAPI:
    with open(file_path, "r") as file:
        d = yaml.safe_load(file)
    return OpenAPI.model_validate(d)

def load_policy(file_path:str)->List[ToolPolicyItem]:
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
    
def symlink_force(target, link_name):
    try:
        os.symlink(target, link_name)
    except FileExistsError:
        os.remove(link_name)
        os.symlink(target, link_name)

def main():
    oas_path = "tau_airline/input/openapi.yml"
    tool_names = ["book_reservation"]
    policy_paths = ["tau_airline/input/BookReservation_fix_5.json"]
    model = "gpt-4o-2024-08-06"
    output_dir = "tau_airline/output"
    now = datetime.now()
    output_path = os.path.join(output_dir, now.strftime("%Y-%m-%d %H:%M:%S"))

    policies = [load_policy(path) for path in policy_paths]
    oas = read_oas(oas_path)
    llm = AzureLitellm(model)

    logger.debug(f"Starting... will save into {output_path}")
    # domain = generate_domain(oas, llm)
    domain = load_domain(f"tau_airline/input/domain.py")
    domain.save(output_path)
    logger.debug(f"domain created")
    # symlink_force(output_path, os.path.join(output_dir, "LAST"))

    for tool_name, tool_poilcy_items in zip(tool_names, policies):
        logger.debug(f"Tool {tool_name}")
        if len(tool_poilcy_items) == 0: continue
        # op_oas = op_only_oas(oas, tool_name)
        op = oas.get_operation_by_operationId(tool_name)
        assert op
        tool_info = ToolInfo(
            tool_name=tool_name, 
            tool_description=op.description,
            policy_items=tool_poilcy_items
        )

        code, tests = generate_function(domain, tool_info, llm, output_path)

if __name__ == '__main__':
    load_dotenv()
    main()