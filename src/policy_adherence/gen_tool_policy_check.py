import ast
import astor
from pydantic import BaseModel
from typing import Dict, List, Tuple
from loguru import logger
from policy_adherence.types import MyFile, ToolPolicy
from policy_adherence.llm.llm_model import LLM_model
# from policy_adherence.pylint import run_pylint

from policy_adherence.tools.pyright import run_pyright
from policy_adherence.tools.pytest import run_unittests
from policy_adherence.utils import call_llm, extract_code_from_llm_response, to_md_bulltets

MAX_TOOL_IMPROVEMENTS = 3
MAX_TEST_GEN_TRIALS = 3

class ToolChecksCodeResult(BaseModel):
    tool: ToolPolicy
    check_file_name: str
    tests_file_name: str

class ToolChecksCodeGenerationResult(BaseModel):
    output_path: str
    domain_file: str
    tools: Dict[str, ToolChecksCodeResult]

class PolicyAdherenceCodeGenerator():
    llm: LLM_model
    cwd: str

    def __init__(self, llm:LLM_model, cwd:str) -> None:
        self.llm = llm
        self.cwd = cwd

    def generate_tools_check_fns(self, tool_policies: List[ToolPolicy], domain:MyFile)->ToolChecksCodeGenerationResult:
        logger.debug(f"Starting... will save into {self.cwd}")

        tools_result: Dict[str, ToolChecksCodeResult] = {}
        for tool in tool_policies:
            if len(tool.policy_items) == 0: continue
            logger.debug(f"Tool {tool.name}")
            
            tool_check_fn, tool_check_tests = self.generate_tool_check_fn(domain, tool, self.cwd)
            tools_result[tool.name] = ToolChecksCodeResult(
                tool = tool,
                check_file_name=tool_check_fn.file_name, 
                tests_file_name=tool_check_tests.file_name,
            )
        
        return ToolChecksCodeGenerationResult(
            output_path=self.cwd,
            domain_file=domain.file_name,
            tools=tools_result
        )

    def _copy_check_fn_stub(self, domain:MyFile, fn_name:str, new_fn_name:str)->MyFile:
        tree = ast.parse(domain.content)
        new_body = []
        new_body.append(ast.ImportFrom(
            module=domain.file_name[:-3],# The module name (without ./)
            names=[ast.alias(name="*", asname=None)],  # Import Type
            level=0            # 0 = absolute import, 1 = relative import (.)
        ))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == fn_name:
                #TODO add history chat messages
                node.name = new_fn_name
                node.returns = ast.Constant(value=None)
                node.body = [ast.Pass()]
                new_body.append(node)
        
        module = ast.Module(body=new_body, type_ignores=[])
        ast.fix_missing_locations(module)
        src= astor.to_source(module)
        return MyFile(file_name=f"{new_fn_name}.py", content=src)

    def _improve_check_fn(self, domain: MyFile, tool: ToolPolicy, previous_version:MyFile, review_comments: List[str], trial=0)->MyFile:
        logger.debug(f"Improving check function... (trial = {trial})")
        check_fn_name = f"check_{tool.name}"
        prompt = f"""You are given:
* a Python file describing the domain. It contains data classes and functions you may use.
* a list of policy items. Policy items have a list of positive and negative examples. 
* current implementation of a Python function, `{check_fn_name}()`.
* a list of review comments on issues that need to be improved in the current implementation.

The goal of the function is to check that ALL policy items hold on the function arguments. 
In particular, running the function on all the positive examples should pass.
For all negative examples, the function should raise an exception with a meaningful message.

If you need to retrieve additional data (that is not in the function arguments), you can call functions defined in the domain.
You need to generate code that improve the current implementation, according to the review comments.
The code must be simple and well documented.

### Domain:
```
### {domain.file_name}

{domain.content}
```

### Policy Items:

{tool.policies_to_md()}


### Current implemtnation
```
### {previous_version.file_name}

{previous_version.content}
```

### Review commnets:

{to_md_bulltets(review_comments)}
"""
        res_content = call_llm(prompt, self.llm)
        body = extract_code_from_llm_response(res_content)
        check_fn = MyFile(file_name=f"{check_fn_name}.py", content=body)
        check_fn.save(self.cwd)
        check_fn.save_as(self.cwd, f"{check_fn_name}_{trial}.py")

        # lint_report = run_pyright(self.cwd, check_fn.file_name)
        # if lint_report.summary.errorCount>0:
        #     MyFile(
        #             file_name=f"{check_fn_name}_{trial}_errors.json", 
        #             content=lint_report.model_dump_json(indent=2)
        #         ).save(self.cwd)
        #     logger.warning(f"Generated function with Python errors.")
            
        #     if trial < MAX_TOOL_IMPROVEMENTS:
        #         return self._improve_check_fn(domain, tool, check_fn, review_comments, trial+1)
        #     raise Exception(f"Generation failed for tool {tool.name}")
        return check_fn
    

    def generate_tool_tests(self, fn_stub:MyFile, tool:ToolPolicy, domain:MyFile, trial=0)-> Tuple[MyFile, List[str]]:
        test_module_name = f"test_check_{tool.name}"
        logger.debug(f"Generating Tests... (trial={trial})")
        prompt = f"""You are given:
* a Python file describing the domain. It contains data classes and interfaces you may use.
* a list of policy items. Policy items have a list of positive and negative examples. 
* an interface of a Python function-under-test, `{test_module_name}()`.

Your task is to write unit tests to check the implementation of the interface-under-test.
The function implemtation should check that ALL policy statements hold on its arguments.
If the arguments violate a policy statement, an exception should be thrown.
Policy statement have positive and negative examples.
For positive-cases, the function should not throw exceptions.
For negative-cases, the function should throw an exception.
Generate one test for each example. 

If an unexpected exception is catched, the test should fail with the exception message.

Name the test using up to 6 representative words (snake_case).

If the function-under-test need to access data from other functions in the domain, you should mock the call and the return value using `unittest.mock.patch`. 
For example, if `check_book_reservation` is the function under test, and it may access the `get_user_details()`:
```
args = ...
user = User(...)
with patch("check_book_reservation.get_user_details", return_value=user):
  check_book_reservation(args)
```

Make sure to indicate test failures using a meaningful message.

### Domain:
```
### {domain.file_name}

{domain.content}
```

### Policy Items:

{tool.policies_to_md()}


### Interface under test
```
### {fn_stub.file_name}

{fn_stub.content}
```"""
        res_content = call_llm(prompt, self.llm)
        body = extract_code_from_llm_response(res_content)
        
        tests = MyFile(file_name=f"{test_module_name}.py", content=body)
        tests.save(self.cwd)
        tests.save_as(self.cwd, f"{test_module_name}_{trial}.py")
        lint_report = run_pyright(self.cwd, tests.file_name)
        if lint_report.errors_only():
            logger.warning(f"Generated tests with Python errors.")
            if trial < MAX_TEST_GEN_TRIALS:
                return self.generate_tool_tests(fn_stub, tool, domain, trial+1)
            raise Exception("Generated tests contain errors")
    
        #syntax ok, try to run it...
        logger.debug(f"Generated Tests... (trial={trial})")
        #still running against a stub. the tests should fail, but the collector should not fail.
        test_report = run_unittests(self.cwd, tests.file_name)
        if not test_report.all_tests_collected_successfully():
            logger.debug(f"Tool {tool.name} unit tests error")
            return self.generate_tool_tests(fn_stub, tool, domain, trial+1)
        
        return tests, test_report.list_errors()

    def generate_tool_check_fn(self, domain: MyFile, tool:ToolPolicy, output_path:str, trial_no=0)->Tuple[MyFile, MyFile]:
        check_fn_name = f"check_{tool.name}"
        check_fn = self._copy_check_fn_stub(domain, tool.name, check_fn_name)
        check_fn.save(output_path)
        check_fn.save_as(self.cwd, f"{check_fn_name}_-1.py")
        
        logger.debug(f"Tool {tool.name} function draft created")

        tests, errors = self.generate_tool_tests(check_fn, tool, domain)
        logger.debug(f"Tests {tests.file_name} successfully created")

        # logger.debug(f"Tool {tool_name} function is {'valid' if valid_fn() else 'invalid'}")
        while trial_no < MAX_TOOL_IMPROVEMENTS and errors:
            logger.debug(f"Tool {tool.name} function has errors. Retrying...")
            check_fn = self._improve_check_fn(domain, tool, check_fn, errors)
            check_fn.save(output_path)
            errors = self._check_fn_is_ok(check_fn, domain, tests, output_path, trial_no)
            trial_no +=1
        
        return check_fn, tests

    def _check_fn_is_ok(self, fn_code: MyFile, domain: MyFile, test_cases:MyFile, output_path:str, trial_no)->List[str]:
        report = run_unittests(output_path, test_cases.file_name, f"_{trial_no}")
        return report.list_errors()