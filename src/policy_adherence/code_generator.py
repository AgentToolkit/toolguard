import ast
import astor
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Tuple
from loguru import logger
from policy_adherence.code import Code
from policy_adherence.llm.llm_model import LLM_model
from policy_adherence.oas import OpenAPI
from policy_adherence.unittests import TestOutcome, run_unittests

class ToolPolicyItem(BaseModel):
    policy: str = Field(..., description="Policy item")
    compliance_examples: Optional[List[str]] = Field(..., description="Case example that complies with the policy")
    violation_examples: Optional[List[str]] = Field(..., description="Case example that violates the policy")

ToolsPolicies = Dict[str, List[ToolPolicyItem]]

class PolicyAdherenceCodeGenerator():
    llm: LLM_model
    output_path: str

    def __init__(self, llm:LLM_model, output_path:str) -> None:
        self.llm = llm
        self.output_path = output_path

    def generate_tools_check_fns(self, oas: OpenAPI, tool_policies: ToolsPolicies, domain:Optional[Code] = None, retries=2)->List[Code]:
        logger.debug(f"Starting... will save into {self.output_path}")

        if not domain:
            domain = self.generate_domain(oas)
        domain.save(self.output_path)
        logger.debug(f"domain created")
        # symlink_force(output_path, os.path.join(output_dir, "LAST"))

        for tool_name, tool_poilcies in tool_policies.items():
            logger.debug(f"Tool {tool_name}")
            if len(tool_poilcies) == 0: continue
            # op_oas = op_only_oas(oas, tool_name)
            op = oas.get_operation_by_operationId(tool_name)
            assert op
            
            code, tests = self.generate_tool_check_fn(domain, tool_name, tool_poilcies, self.output_path)
        return []

    def generate_domain(self, oas: OpenAPI, retries=2)->Code:
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
        res_content = self._call_llm(prompt)
        code = self._extract_code_from_response(res_content)

        try:
            ast.parse(code) #check syntax
            return Code(file_name="domain.py", content=code)
        except Exception as ex:
            logger.warning(f"Generated domain have invalid syntax. {str(ex)}")
            if retries>1:
                return self.generate_domain(oas, retries=retries-1) #retry
            raise ex

    def _policy_statements(self, policies:List[ToolPolicyItem]):
        s = ""
        for i, item in enumerate(policies):
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

    def _copy_check_fn_stub(self, domain:Code, fn_name:str, new_fn_name:str)->Code:
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
        src= astor.to_source(module)
        return Code(file_name=f"{new_fn_name}.py", content=src)

    def generate_tool_tests(self, checker_fn:Code, tool_name:str, policies:List[ToolPolicyItem], retries=2)-> Code:
        logger.debug(f"Generating Tests... (retries={retries})")
        prompt = f"""You are given a function stub in Python. This function is under test:
```
### {checker_fn.file_name}
{checker_fn.content}
```
make sure to import it from {checker_fn.file_name}.

You are also given with policy statements that the function under test should comply with.
For each statement, you are also provided with positive and negative examples.

Your task is to write unit tests to check that the function implementation check the policy statements.
Generate one test for each policy statement example.
For negative examples, check that the funtion under test raise a `builtins.Exception`.
For positive cases check that no exception raised.
Indicate test failures using a meaningful message that also contain the policy statement and the example.

{self._policy_statements(policies)}
    """
        res_content = self._call_llm(prompt)
        code = self._extract_code_from_response(res_content)
        
        try:
            ast.parse(code)
            return Code(file_name=f"test_check_{tool_name}.py", content=code)
        except Exception as ex:
            logger.warning(f"Generated tests have invalid syntax. {str(ex)}")
            if retries>0:
                return self.generate_tool_tests(checker_fn, tool_name, policies, retries=retries-1)
            raise ex

    def _improve_check_fn(self, domain: Code, tool_name: str, policies:List[ToolPolicyItem], retries=2)->Code:
        logger.debug(f"Generated function... (retry = {retries})")
        check_fn_name = f"check_{tool_name}"
        fn_signature = self._copy_check_fn_stub(domain, tool_name, check_fn_name)
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
{self._policy_statements(policies)}
    """
        res_content = self._call_llm(prompt)
        code = self._extract_code_from_response(res_content)

        try:
            ast.parse(code)
            return Code(file_name=f"{check_fn_name}.py", content=code)
        except Exception as ex:
            logger.warning(f"Generated function failed. Syntax error. {str(ex)}")
            if retries>0:
                return self._improve_check_fn(domain, tool_name, policies, retries-1)
            raise ex

    def generate_tool_check_fn(self, domain: Code, tool_name:str, policies:List[ToolPolicyItem], output_path:str, retries=3)->Tuple[Code, Code]:
        valid_fn_code = self._copy_check_fn_stub(domain, tool_name, f"check_{tool_name}")
        valid_fn_code.save(output_path)
        logger.debug(f"Tool {tool_name} function draft created")

        tests = self.generate_tool_tests(valid_fn_code, tool_name, policies)
        tests.save(output_path)
        report = run_unittests(output_path) #still running against a stub. the tests should fail, but the collector should not fail.
        if not report.all_tests_collected():
            logger.debug(f"Tool {tool_name} unit tests error")
            # TODO retry
        logger.debug(f"Tool {tool_name} unit tests created")

        valid_fn = lambda: self._check_fn_is_ok(valid_fn_code, domain, tests, output_path)
        logger.debug(f"Tool {tool_name} function is {'valid' if valid_fn() else 'invalid'}")
        while retries > 0 and not valid_fn():
            logger.debug(f"Tool {tool_name} function is invalid. Retrying...")
            valid_fn_code = self._improve_check_fn(domain, tool_name, policies)
            valid_fn_code.save(output_path)
            retries -=1
        
        return valid_fn_code, tests

    def _check_fn_is_ok(self, fn_code: Code, domain: Code, test_cases:Code, output_path:str):
        report = run_unittests(output_path)
        return report.all_tests_passed()
        # lint
        # hallucinations
        # llm all poliCIES ARE COVERED?
        # llm code that is not described in policy?
        return True

    def _extract_code_from_response(self, resp:str)->str:
        start_code_token = "```python\n"
        end_code_token = "```"
        start = resp.find(start_code_token) + len(start_code_token)
        end = resp.rfind(end_code_token)
        return resp[start:end]
    
    def _call_llm(self, prompt:str):
        msgs = [{"role":"system", "content": prompt}]
        res = self.llm.chat_json(msgs)
        res_content = res.choices[0].message.content # type: ignore
        return res_content