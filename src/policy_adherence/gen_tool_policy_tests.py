

from typing import List, Tuple
from loguru import logger

from policy_adherence.llm.llm_model import LLM_model
from policy_adherence.utils import call_llm, extract_code_from_llm_response
from policy_adherence.types import Code, ToolPolicy, ToolPolicyItem
from policy_adherence.tools.pyright import run_pyright
from policy_adherence.tools.pytest import run_unittests

MAX_TRIALS = 3
class ToolPolicyTestsGenerator:
    llm: LLM_model
    cwd: str

    def __init__(self, llm:LLM_model, cwd:str) -> None:
        self.llm = llm
        self.cwd = cwd

    def generate_tool_tests(self, fn_stub:Code, tool:ToolPolicy, domain:Code, trial=0)-> Tuple[Code, List[str]]:
        fn_name = f"test_check_{tool.name}"
        logger.debug(f"Generating Tests... (trial={trial})")
        prompt = f"""You are given:
* a Python file describing the domain. It contains data classes and interfaces you may use.
* a list of policy items. Policy items have a list of positive and negative examples. 
* an interface of a Python function-under-test, `{fn_name}()`.

Your task is to write unit tests to check the implementation of the interface-under-test.
The function implemtation needs to check that all the policy statements hold on its arguments.
If the arguments violate a policy statement, an exception should be thrown.
Policy statement have positive and negative examples.
For positive-cases, the function should not throw exceptions.
For negative-cases, the function should throw an exception.
Generate one test for each example. 
Name the test using up to 6 representative words (snake_case).
Indicate test failures using a meaningful message.

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
        
        tests = Code(file_name=f"{fn_name}.py", content=body)
        tests.save(self.cwd)
        lint_report = run_pyright(self.cwd, tests.file_name)
        if lint_report.list_errors():
            logger.warning(f"Generated tests with Python errors.")
            if trial < MAX_TRIALS:
                return self.generate_tool_tests(fn_stub, tool, domain, trial+1)
            raise Exception("Generated tests contain errors")
    
        #syntax ok, try to run it...
        logger.debug(f"Generated Tests... (retries={trial})")
        #still running against a stub. the tests should fail, but the collector should not fail.
        test_report = run_unittests(self.cwd)
        if not test_report.all_tests_collected_successfully():
            logger.debug(f"Tool {tool.name} unit tests error")
            return self.generate_tool_tests(fn_stub, tool, domain, trial+1)
        
        return tests, test_report.list_errors()
