import ast
import astor
from pydantic import BaseModel
from typing import Dict, List, Tuple
from loguru import logger
from policy_adherence.prompts import do_generate_tool_tests, do_improve_fn
from policy_adherence.types import GenFile, ToolPolicy
from policy_adherence.llm.llm_model import LLM_model

from policy_adherence.tools.pyright import pyright_config, run_pyright
from policy_adherence.tools.pytest import run_unittests
from policy_adherence.utils import extract_code_from_llm_response

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

    def check_fn_name(self, tool_name:str)->str:
        return f"check_{tool_name}"
    
    def check_fn_module_name(self, tool_name:str)->str:
        return f"check_{tool_name}"
    
    def test_fn_name(self, tool_name:str)->str:
        return f"test_check_{tool_name}"
    
    def test_fn_module_name(self, tool_name:str)->str:
        return f"test_check_{tool_name}"
    
    def generate_tools_check_fns(self, tool_policies: List[ToolPolicy], domain:GenFile)->ToolChecksCodeGenerationResult:
        logger.debug(f"Starting... will save into {self.cwd}")
        pyright_config().save(self.cwd)

        tools_result: Dict[str, ToolChecksCodeResult] = {}
        for tool in tool_policies:
            if len(tool.policy_items) == 0: continue
            logger.debug(f"Tool {tool.name}")
            
            tool_check_fn, tool_check_tests = self.generate_tool_check_fn(domain, tool)
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

    def generate_tool_check_fn(self, domain: GenFile, tool:ToolPolicy, trial_no=0)->Tuple[GenFile, GenFile]:
        check_fn_name = f"check_{tool.name}"
        check_fn = self._copy_check_fn_stub(domain, tool.name, check_fn_name)
        check_fn.save(self.cwd)
        check_fn.save_as(self.cwd, f"-1_{check_fn_name}.py")
        
        logger.debug(f"Tool {tool.name} function draft created")

        tests = self.generate_tool_tests(check_fn, tool, domain)
        logger.debug(f"Tests {tests.file_name} successfully created")
        # logger.debug(f"Tool {tool_name} function is {'valid' if valid_fn() else 'invalid'}")
        while True:
            errors = run_unittests(self.cwd, tests.file_name, str(trial_no)).list_errors()
            if not errors: 
                return check_fn, tests
            if trial_no >= MAX_TOOL_IMPROVEMENTS:
                raise Exception(f"Could not generate check function for tool {tool.name}")
            
            logger.debug(f"Tool {tool.name} function has errors. Retrying...")
            check_fn = self._improve_check_fn(domain, tool, check_fn, errors)
            trial_no +=1


    def _copy_check_fn_stub(self, domain:GenFile, fn_name:str, new_fn_name:str)->GenFile:
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
        return GenFile(file_name=f"{new_fn_name}.py", content=src)

    def _improve_check_fn(self, domain: GenFile, tool: ToolPolicy, prev_version:GenFile, review_comments: List[str], trial=0)->GenFile:
        fn_name = self.check_fn_name(tool.name)
        logger.debug(f"Improving check function... (trial = {trial})")
        res_content = do_improve_fn(self.llm, fn_name, domain, tool, prev_version, review_comments)
        body = extract_code_from_llm_response(res_content)
        check_fn = GenFile(
            file_name=f"{self.check_fn_module_name(tool.name)}.py", 
            content=body
        )
        check_fn.save(self.cwd)
        check_fn.save_as(self.cwd, f"{trial}_{self.check_fn_module_name(tool.name)}.py")

        lint_report = run_pyright(self.cwd, check_fn.file_name)
        if lint_report.summary.errorCount>0:
            GenFile(
                    file_name=f"{trial}_{self.check_fn_module_name(tool.name)}_errors.json", 
                    content=lint_report.model_dump_json(indent=2)
                ).save(self.cwd)
            logger.warning(f"Generated function with Python errors.")
            
            if trial < MAX_TOOL_IMPROVEMENTS:
                return self._improve_check_fn(domain, tool, check_fn, review_comments, trial+1)
            raise Exception(f"Generation failed for tool {tool.name}")
        return check_fn
    
    def generate_tool_tests(self, fn_stub:GenFile, tool:ToolPolicy, domain:GenFile, trial=0)-> GenFile:
        logger.debug(f"Generating Tests... (trial={trial})")
        tests = self._generate_tool_tests(fn_stub, tool, domain)
        tests.save_as(self.cwd, f"{trial}_{tests.file_name}")

        lint_report = run_pyright(self.cwd, tests.file_name)
        if lint_report.summary.errorCount>0:
            logger.warning(f"Generated tests with Python errors.")
            if trial < MAX_TEST_GEN_TRIALS:
                return self.generate_tool_tests(fn_stub, tool, domain, trial+1)
            raise Exception("Generated tests contain errors")
    
        #syntax ok, try to run it...
        logger.debug(f"Generated Tests... (trial={trial})")
        #still running against a stub. the tests should fail, but the collector should not fail.
        test_report = run_unittests(self.cwd, tests.file_name)
        if test_report.all_tests_collected_successfully():
            reviews = self._review_generated_tool_tests(domain, tool, tests)
            if reviews:
                #TODO 
                print(reviews)
            return tests
        
        logger.debug(f"Tool {tool.name} tests error. Retrying...")
        return self.generate_tool_tests(fn_stub, tool, domain, trial+1)

    def _generate_tool_tests(self, fn_stub:GenFile, tool:ToolPolicy, domain:GenFile)-> GenFile:
        test_fn_name = self.test_fn_name(tool.name)
        res_content = do_generate_tool_tests(self.llm, test_fn_name, fn_stub, tool, domain)
        body = extract_code_from_llm_response(res_content)
        tests = GenFile(file_name=f"{self.test_fn_module_name(tool.name)}.py", content=body)
        tests.save(self.cwd)
        return tests

    def _review_generated_tool_tests(self, domain: GenFile, tool:ToolPolicy, tests: GenFile)-> List[str]:
        return []