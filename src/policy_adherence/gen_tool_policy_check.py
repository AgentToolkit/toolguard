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
import policy_adherence.prompts as prompts
from policy_adherence.types import SourceFile, ToolPolicy, ToolPolicyItem
import policy_adherence.tools.venv as venv
import policy_adherence.tools.pyright as pyright
import policy_adherence.tools.pytest as pytest
from policy_adherence.utils import extract_code_from_llm_response

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

class PolicyAdherenceCodeGenerator():
    cwd: str

    def __init__(self, cwd:str) -> None:
        self.cwd = cwd
        self.debug_dir = os.path.join(cwd, "debug")
        os.makedirs(self.debug_dir, exist_ok=True)

    def check_fn_name(self, tool_name:str)->str:
        return f"check_{tool_name}"
    
    def check_fn_module_name(self, tool_name:str)->str:
        return f"check_{tool_name}"
    
    def test_fn_name(self, tool_name:str)->str:
        return f"test_check_{tool_name}"
    
    def test_fn_module_name(self, tool_name:str)->str:
        return self.test_fn_name(tool_name)
    
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
        tool_futures = [self.generate_tool_tests_and_check_fn(domain, common, tool) for tool in tools_with_poilicies]
        tool_results = await asyncio.gather(*tool_futures)
        tools_result = {tool.name:res 
            for tool, res 
            in zip(tools_with_poilicies, tool_results)
        }        
        return ToolChecksCodeGenerationResult(
            output_path=self.cwd,
            domain_file=domain.file_name,
            tools=tools_result
        )

    async def generate_tool_tests_and_check_fn(self, domain: SourceFile, common:SourceFile, tool:ToolPolicy, trial_no=0)->ToolChecksCodeResult:
        check_fn_name = f"check_{tool.name}"
        check_fn = self._create_check_fn_signature(domain, common, tool.name, check_fn_name)
        check_fn.save(self.cwd)
        self._save_debug(check_fn, f"-1_{check_fn_name}.py")
        
        logger.debug(f"Tool {tool.name} function draft created")

        dependent_tools = await self.dependent_tools(tool, domain)
        logger.debug(f"Dependencies of {tool.name}: {dependent_tools}")

        test = await self.generate_tool_policy_tests(check_fn, tool, common, domain, dependent_tools) 
        while True:
            errors = pytest.run(self.cwd, '').list_errors()
            if not errors: 
                return ToolChecksCodeResult(tool=tool, check_fn_src=check_fn, test_files=[test])
            if trial_no >= MAX_TOOL_IMPROVEMENTS:
                raise Exception(f"Could not generate check function for tool {tool.name}")
            
            logger.debug(f"Tool {tool.name} function has errors. Retrying...")
            check_fn = await self._improve_check_fn(domain, tool, check_fn, errors, trial_no)
            trial_no +=1

    async def dependent_tools(self, tool: ToolPolicy, domain: SourceFile)->set[str]:
        async def item_dependencies(policy_item: ToolPolicyItem):
            return await anyio.to_thread.run_sync(
                lambda: prompts.tool_information_dependencies(policy_item.name, policy_item.policy, domain)
            )
        all_deps = await asyncio.gather(*[item_dependencies(item) for item in tool.policy_items])
        uniq_deps = set(item for sublist in all_deps for item in sublist)
        return uniq_deps

    def _create_check_fn_signature(self, domain:SourceFile, common: SourceFile, fn_name:str, new_fn_name:str)->SourceFile:
        new_body = []

        #runtime
        new_body.append(ast.ImportFrom(
            module=common.file_name[:-3],# The module name (without ./)
            names=[ast.alias(name="*", asname=None)],
            level=0
        ))

        #domain
        tree = ast.parse(domain.content)
        new_body.append(ast.ImportFrom(
            module=domain.file_name[:-3],# The module name (without ./)
            names=[ast.alias(name="*", asname=None)],  # Import Type
            level=0            # 0 = absolute import, 1 = relative import (.)
        ))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == fn_name:
                #TODO add history chat messages
                node.name = new_fn_name#rename
                node.returns = ast.Constant(value=None)
                node.args.args.append(
                    ast.arg(arg="chat_history", annotation=ast.Name(id="ChatHistory", ctx=ast.Load()))
                )
                node.body = [ast.Pass()]
                new_body.append(node)
        
        module = ast.Module(body=new_body, type_ignores=[])
        ast.fix_missing_locations(module)
        src= astor.to_source(module)
        return SourceFile(file_name=f"{new_fn_name}.py", content=src)

    async def _improve_check_fn(self, domain: SourceFile, tool: ToolPolicy, prev_version:SourceFile, review_comments: List[str], trial=0)->SourceFile:
        module_name = self.check_fn_module_name(tool.name)
        logger.debug(f"Improving check function... (trial = {trial})")

        policies = [item.policy for item in tool.policy_items]
        res_content = await anyio.to_thread.run_sync(lambda:
            prompts.improve_tool_check_fn(prev_version, domain, policies, review_comments)
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
                raise Exception(f"Generation failed for tool {tool.name}")
            errors = [d.message for d in lint_report.generalDiagnostics if d.severity == pyright.ERROR]
            return await self._improve_check_fn(domain, tool, check_fn, errors, trial+1)
        return check_fn
    
    async def generate_tool_policy_tests(self, fn_stub:SourceFile, tool:ToolPolicy, common:SourceFile, domain:SourceFile, dependent_tools: set[str], trial=0)-> SourceFile:
        logger.debug(f"Generating Tests {tool.name}... (trial={trial})")
        tests = await self._generate_tool_policy_tests(fn_stub, tool, common, domain, dependent_tools)
        self._save_debug(tests, f"{trial}_{tests.file_name}")

        lint_report = pyright.run(self.cwd, tests.file_name, PY_ENV)
        if lint_report.summary.errorCount>0:
            logger.warning(f"Generated tests with Python errors {tests.file_name}.")
            if trial < MAX_TEST_GEN_TRIALS:
                return await self.generate_tool_policy_tests(fn_stub, tool, common, domain, dependent_tools, trial+1)
            raise Exception("Generated tests contain errors")
    
        #syntax ok, try to run it...
        logger.debug(f"Generated Tests... (trial={trial})")
        #still running against a stub. the tests should fail, but the collector should not fail.
        test_report = pytest.run(self.cwd, tests.file_name)
        report_file_name = f"{tool.name}_report.json"
        SourceFile(
            file_name=report_file_name, 
            content=test_report.model_dump_json(indent=2)
        ).save_as(self.debug_dir, report_file_name)

        if test_report.all_tests_collected_successfully():
            reviews = self._review_generated_tool_tests(domain, tool, tests)
            if reviews:
                #TODO 
                print(reviews)
            return tests
        
        logger.debug(f"Tool {tool.name} tests error. Retrying...")
        return await self.generate_tool_policy_tests(fn_stub, tool, common, domain, dependent_tools, trial+1)

    async def _generate_tool_policy_tests(self, fn_stub:SourceFile, tool:ToolPolicy, common: SourceFile, domain:SourceFile, dependent_tools: set[str])-> SourceFile:
        res_content = await anyio.to_thread.run_sync(
            lambda: prompts.generate_tool_policy_tests(fn_stub, tool, common, domain, dependent_tools)
        )
        body = extract_code_from_llm_response(res_content)
        tests = SourceFile(file_name=f"{self.test_fn_module_name(tool.name)}.py", content=body)
        tests.save(self.cwd)
        return tests

    def _review_generated_tool_tests(self, domain: SourceFile, tool:ToolPolicy, tests: SourceFile)-> List[str]:
        return []