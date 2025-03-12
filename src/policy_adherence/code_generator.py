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

MAX_TOOL_IMPROVEMENTS = 3

class ToolChecksCodeResult(BaseModel):
    tool_name: str
    check_file_name: str
    tests_file_name: str
    policies: List[ToolPolicyItem]

class ToolChecksCodeGenerationResult(BaseModel):
    output_path: str
    domain_file: str
    tools: Dict[str, ToolChecksCodeResult]

class PolicyAdherenceCodeGenerator():
    llm: LLM_model
    output_path: str

    def __init__(self, llm:LLM_model, output_path:str) -> None:
        self.llm = llm
        self.output_path = output_path

    def generate_tools_check_fns(self, oas: OpenAPI, tool_policies: ToolsPolicies, domain:Optional[Code] = None, retries=2)->ToolChecksCodeGenerationResult:
        logger.debug(f"Starting... will save into {self.output_path}")
        if not domain:
            domain = self.generate_domain(oas)
        domain.save(self.output_path)
        logger.debug(f"domain created")
        tools_result: Dict[str, ToolChecksCodeResult] = {}
        for tool_name, tool_poilcies in tool_policies.items():
            if len(tool_poilcies) == 0: continue
            logger.debug(f"Tool {tool_name}")
            
            tool_check_fn, tool_check_tests = self.generate_tool_check_fn(domain, tool_name, tool_poilcies, self.output_path)
            tools_result[tool_name] = ToolChecksCodeResult(
                tool_name=tool_name,
                check_file_name=tool_check_fn.file_name, 
                tests_file_name=tool_check_tests.file_name,
                policies=tool_poilcies
            )
        
        return ToolChecksCodeGenerationResult(
            output_path=self.output_path,
            domain_file=domain.file_name,
            tools=tools_result
        )

    def generate_domain(self, oas: OpenAPI, retries=2)->Code:
        logger.debug(f"Generating domain... (retry = {retries})")
        prompt = f"""Given an OpenAPI Spec, generate Python code that include all the data-types as Pydantic data-classes. 
For data-classes fields, make all fields optional with default `None`.
For each operation, create a function stub.
The function name comes from the operation operationId.
The function argument names and types come from the operation parameters and requestBody.
The function return-type comes from the operation 200 response.
Both, the function arguments and return-type, should be specific (avoid Dict), and should refer to the generated data-classes.
Add the operation description as the function documentation.

```
{oas.model_dump_json(indent=2)}
```"""
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

    def _bulltets(self, items: List[str])->str:
        s = ""
        for item in items:
            s+=f"* {item}\n"
        return s
    
    def _policy_statements(self, policies:List[ToolPolicyItem]):
        s = ""
        for i, item in enumerate(policies):
            s+= f"## Policy item {i+1}"
            s+=f"{item.policy}\n"
            if item.compliance_examples:
                s+=f"### Positive examples\n{self._bulltets(item.compliance_examples)}"
            if item.violation_examples:
                s+=f"### Negative examples\n{self._bulltets(item.violation_examples)}"
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

    def generate_tool_tests(self, checker_fn:Code, tool_name:str, policies:List[ToolPolicyItem], retries=2)-> Tuple[Code, List[str]]:
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
            tests = Code(file_name=f"test_check_{tool_name}.py", content=code)
        except Exception as ex:
            logger.warning(f"Generated tests with syntax errors. {str(ex)}")
            if retries>0:
                return self.generate_tool_tests(checker_fn, tool_name, policies, retries=retries-1)
            raise ex
        
        #syntax ok, try to run it...
        logger.debug(f"Generated Tests... (retries={retries})")
        tests.save(self.output_path)
        #still running against a stub. the tests should fail, but the collector should not fail.
        report = run_unittests(self.output_path)
        if not report.all_tests_collected_successfully():
            logger.debug(f"Tool {tool_name} unit tests error")
            return self.generate_tool_tests(checker_fn, tool_name, policies, retries=retries-1)
        
        return tests, report.list_errors()

    def _improve_check_fn(self, domain: Code, tool_name: str, tool_policies:List[ToolPolicyItem], previous_version:Code, review_comments: List[str], retries=2)->Code:
        logger.debug(f"Improving check function... (retry = {retries})")
        check_fn_name = f"check_{tool_name}"
        prompt = f"""You are given:
* a Python file describing the domain. It contains data classes and functions you may use.
* a list of policy items. Policy items have a list of positive and negative examples. 
* current implementation of a Python function, `{check_fn_name}()`.
* a list of review comments on issues that need to be improved in the current implementation.

The goal of the function is to check that all the policy items hold on the given input. 
In particular, all positive examples should pass silently.
For all negative examples, the function should raise a meaningful exception.
If you need to retrieve additional data (that is not in the function arguments), you can call functions defined in the domain.
You need to generate code that improve the current implementation, according to the review comments.
The code must be simple and well documented.

# Domain:
```
### domain.file_name
{domain.content}
```

# Policy Items:
{self._policy_statements(tool_policies)}


# Current implemtnation
```
### {previous_version.file_name}
{previous_version.content}
```

# Review commnets:
```
{self._bulltets(review_comments)}
```
    """
        res_content = self._call_llm(prompt)
        code = self._extract_code_from_response(res_content)

        try:
            ast.parse(code)
            return Code(file_name=f"{check_fn_name}.py", content=code)
        except Exception as ex:
            logger.warning(f"Generated function failed. Syntax error. {str(ex)}")
            if retries>0:
                return self._improve_check_fn(domain, tool_name, tool_policies, code, [str(ex)], retries-1)
            raise ex

    def generate_tool_check_fn(self, domain: Code, tool_name:str, policies:List[ToolPolicyItem], output_path:str, trial_no=0)->Tuple[Code, Code]:
        check_fn = self._copy_check_fn_stub(domain, tool_name, f"check_{tool_name}")
        check_fn.save(output_path)
        logger.debug(f"Tool {tool_name} function draft created")

        tests = self.generate_tool_tests(check_fn, tool_name, policies)
        logger.debug(f"Tool {tool_name} unit tests successfully created")

        valid_fn = lambda: self._check_fn_is_ok(check_fn, domain, tests, output_path)
        # logger.debug(f"Tool {tool_name} function is {'valid' if valid_fn() else 'invalid'}")
        while trial_no < MAX_TOOL_IMPROVEMENTS and not valid_fn():
            logger.debug(f"Tool {tool_name} function is invalid. Retrying...")
            check_fn = self._improve_check_fn(domain, tool_name, policies, check_fn, review_comments)
            check_fn.save(output_path)
            trial_no +=1
        
        return check_fn, tests

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