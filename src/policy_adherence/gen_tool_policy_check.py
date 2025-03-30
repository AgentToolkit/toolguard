import ast
import asyncio
import os
from pathlib import Path
import anyio
import anyio.to_thread
import shutil
import astor
from pydantic import BaseModel
from typing import Dict, List
from loguru import logger
from policy_adherence.check_fn import check_fn_module_name, check_fn_name, create_initial_check_fns, replace_fn_body
from policy_adherence.common.array import find
import policy_adherence.prompts as prompts
from policy_adherence.types import SourceFile, ToolPolicy, ToolPolicyItem, ToolPolicyItem
import policy_adherence.tools.venv as venv
import policy_adherence.tools.pyright as pyright
import policy_adherence.tools.pytest as pytest
from policy_adherence.utils import extract_code_from_llm_response, py_extension, py_name

MAX_TOOL_IMPROVEMENTS = 5
MAX_TEST_GEN_TRIALS = 3
PY_ENV = "my_env"
PY_PACKAGES = ["pydantic"] #, "litellm"
RUNTIME_COMMON = "common.py"

class ToolChecksCodeResult(BaseModel):
    tool: ToolPolicy
    check_fn_src: SourceFile
    test_files: List[SourceFile]

class ToolChecksCodeGenerationResult(BaseModel):
    output_path: str
    domain_file: str
    tools: Dict[str, ToolChecksCodeResult]


def test_fn_name(name:str)->str:
    return py_name(f"test_check_{name}")

def test_fn_module_name(name:str)->str:
    return py_name(test_fn_name(name))

class PolicyAdherenceCodeGenerator():
    cwd: str

    def __init__(self, cwd:str) -> None:
        self.cwd = cwd
        self.debug_dir = os.path.join(cwd, "debug")
        os.makedirs(self.debug_dir, exist_ok=True)
    
    def _save_debug(self, src:SourceFile, file_name:str):
        src.save_as(self.debug_dir, file_name)
    
    async def generate_tools_check_fns(self, tool_policies: List[ToolPolicy], domain:SourceFile)->ToolChecksCodeGenerationResult:
        logger.debug(f"Starting... will save into {self.cwd}")
        venv.run(os.path.join(self.cwd, PY_ENV), PY_PACKAGES)
        pyright.config().save(self.cwd)

        common_file = os.path.join(self.cwd, RUNTIME_COMMON)
        shutil.copy(
            os.path.join(Path(__file__).parent, "_runtime_common.py"),
            common_file
        )
        common = SourceFile.load_from(common_file)

        tools_with_poilicies = [tool for tool in tool_policies if len(tool.policy_items) > 0]
        tool_results = await asyncio.gather(*[
            self.generate_tool_tests_and_check_fn(domain, common, tool) 
            for tool in tools_with_poilicies
        ])
        tools_result = {tool.name:res 
            for tool, res 
            in zip(tools_with_poilicies, tool_results)
        }        
        return ToolChecksCodeGenerationResult(
            output_path=self.cwd,
            domain_file=domain.file_name,
            tools=tools_result
        )

    async def generate_tool_tests_and_check_fn(self, domain: SourceFile, common:SourceFile, tool:ToolPolicy)->ToolChecksCodeResult:
        check_module = create_initial_check_fns(domain, common, tool, self.cwd)
        self._save_debug(check_module, f"-1_{check_module.file_name}")
        
        logger.debug(f"Tool {tool.name} function draft created")
        
        tests = await asyncio.gather(* [
            self.generate_tool_item_tests(check_module, tool_item, common, domain)
            for tool_item in tool.policy_items 
        ])

        check_fns = await asyncio.gather(* [
            self._generate_tool_check_fn(domain, check_module, tool_item, tests)
            for tool_item in tool.policy_items 
        ])
        for check_fn, tool_item in zip(check_fns, tool.policy_items):
            check_module = replace_fn_body(check_fn, check_module, check_fn_name(tool_item.name), self.cwd)
        
        return ToolChecksCodeResult(
            tool=tool,
            check_fn_src=check_module,
            test_files=tests
        )

    async def _generate_tool_check_fn(self, domain: SourceFile, check_fn:SourceFile, tool_item:ToolPolicyItem, tests:List[SourceFile])->SourceFile:
        trial_no = 0
        while trial_no < MAX_TOOL_IMPROVEMENTS:
            errors = pytest.run(self.cwd, py_extension(test_fn_module_name(tool_item.name))).list_errors()
            if not errors: 
                return check_fn
            
            logger.debug(f"Tool {tool_item.name} check function unit-tests failed. Retrying...")
            check_fn = await self._improve_check_fn(domain, tool_item, check_fn, errors, trial_no)
            trial_no +=1
        
        raise Exception(f"Could not generate check function for tool {tool_item.name}")

    async def dependent_tools(self, tool_item: ToolPolicyItem, domain: SourceFile)->set[str]:
        deps = await anyio.to_thread.run_sync(
            lambda: prompts.tool_information_dependencies(tool_item.name, tool_item.description, domain)
        )
        return set(deps)
        # all_deps = await asyncio.gather(*[item_dependencies(item) for item in tool_item.policy_items])
        # uniq_deps = set(item for sublist in all_deps for item in sublist)
        # return uniq_deps

    async def _improve_check_fn(self, domain: SourceFile, tool_item: ToolPolicyItem, prev_version:SourceFile, review_comments: List[str], trial=0)->SourceFile:
        module_name = check_fn_module_name(tool_item.name)
        logger.debug(f"Improving check function... (trial = {trial})")

        res_content = await anyio.to_thread.run_sync(lambda:
            prompts.improve_tool_check_fn(prev_version, domain, tool_item, review_comments)
        )
        body = extract_code_from_llm_response(res_content)
        check_fn = SourceFile(
            file_name=f"{module_name}.py", 
            content=body
        )
        check_fn.save(self.cwd)
        self._save_debug(check_fn, f"{trial}_{module_name}.py")

        lint_report = pyright.run(self.cwd, check_fn.file_name, PY_ENV)
        if lint_report.summary.errorCount>0:
            SourceFile(
                    file_name=f"{trial}_{module_name}_errors.json", 
                    content=lint_report.model_dump_json(indent=2)
                ).save(self.cwd)
            logger.warning(f"Generated function with {lint_report.summary.errorCount} errors.")
            
            if trial >= MAX_TOOL_IMPROVEMENTS:
                raise Exception(f"Generation failed for tool {tool_item.name}")
            errors = [d.message for d in lint_report.generalDiagnostics if d.severity == pyright.ERROR]
            return await self._improve_check_fn(domain, tool_item, check_fn, errors, trial+1)
        return check_fn
    
    async def generate_tool_item_tests(self, fn_stub:SourceFile, tool_item:ToolPolicyItem, common:SourceFile, domain:SourceFile, trial=0)-> SourceFile:
        logger.debug(f"Generating Tests {tool_item.name}... (trial={trial})")
        dependent_tools = await self.dependent_tools(tool_item, domain)
        logger.debug(f"Dependencies of {tool_item.name}: {dependent_tools}")

        tests = await self._generate_tool_item_tests(fn_stub, tool_item, common, domain, dependent_tools)
        self._save_debug(tests, f"{trial}_{tests.file_name}")

        lint_report = pyright.run(self.cwd, tests.file_name, PY_ENV)
        if lint_report.summary.errorCount>0:
            logger.warning(f"Generated tests with Python errors {tests.file_name}.")
            if trial < MAX_TEST_GEN_TRIALS:
                return await self.generate_tool_item_tests(fn_stub, tool_item, common, domain, trial+1)
            raise Exception("Generated tests contain errors")
    
        #syntax ok, try to run it...
        logger.debug(f"Generated Tests... (trial={trial})")
        #still running against a stub. the tests should fail, but the collector should not fail.
        test_report = pytest.run(self.cwd, tests.file_name)
        report_file_name = f"{tool_item.name}_report.json"
        SourceFile(
            file_name=report_file_name, 
            content=test_report.model_dump_json(indent=2)
        ).save_as(self.debug_dir, report_file_name)

        if test_report.all_tests_collected_successfully():
            reviews = self._review_generated_tool_tests(domain, tool_item, tests)
            if reviews:
                #TODO 
                print(reviews)
            return tests
        
        logger.debug(f"Tool {tool_item.name} tests error. Retrying...")
        return await self.generate_tool_item_tests(fn_stub, tool_item, common, domain, trial+1)

    async def _generate_tool_item_tests(self, fn_stub:SourceFile, tool_item:ToolPolicyItem, common: SourceFile, domain:SourceFile, dependent_tools: set[str])-> SourceFile:
        fn_name = check_fn_name(tool_item.name)
        res_content = await anyio.to_thread.run_sync(
            lambda: prompts.generate_tool_item_tests(fn_name, fn_stub, tool_item, common, domain, dependent_tools)
        )
        body = extract_code_from_llm_response(res_content)
        tests = SourceFile(file_name=f"{test_fn_module_name(tool_item.name)}.py", content=body)
        tests.save(self.cwd)
        return tests

    def _review_generated_tool_tests(self, domain: SourceFile, tool:ToolPolicyItem, tests: SourceFile)-> List[str]:
        return []
 