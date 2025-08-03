import inspect
import os
import asyncio
from pathlib import Path
import logging
from os.path import join
from typing import Callable, List, Tuple

from toolguard.common import py
from toolguard.common.str import to_snake_case
from toolguard.data_types import DEBUG_DIR, TESTS_DIR, Domain, FileTwin, RuntimeDomain, ToolPolicy, ToolPolicyItem, ToolPolicyItem
from toolguard.gen_py.consts import guard_fn_module_name, guard_fn_name, guard_item_fn_module_name, guard_item_fn_name, test_fn_module_name
from toolguard.runtime import ToolGuardCodeResult, find_class_in_module, load_module_from_path
import toolguard.utils.pytest as pytest
import toolguard.utils.pyright as pyright
from toolguard.gen_py.prompts.gen_tests import generate_tool_item_tests, improve_tool_tests
from toolguard.gen_py.prompts.improve_guard import improve_tool_guard_fn
from toolguard.gen_py.prompts.python_code import PythonCodeModel
from toolguard.gen_py.prompts.tool_dependencies import tool_dependencies
from toolguard.gen_py.templates import load_template

logger = logging.getLogger(__name__)

MAX_TOOL_IMPROVEMENTS = 5
MAX_TEST_GEN_TRIALS = 3

class ToolGuardGenerator:
    app_name: str
    py_path: str
    tool_policy: ToolPolicy
    domain: RuntimeDomain
    common: FileTwin

    def __init__(self, app_name: str, tool_policy: ToolPolicy, py_path: str, domain: RuntimeDomain, py_env:str) -> None:
        self.py_path = py_path
        self.app_name = app_name
        self.tool_policy = tool_policy
        self.domain = domain
        self.py_env = py_env

    def start(self):
        app_path = join(self.py_path, to_snake_case(self.app_name))
        os.makedirs(app_path, exist_ok=True)
        os.makedirs(join(app_path, to_snake_case(self.tool_policy.tool_name)), exist_ok=True)
        os.makedirs(join(self.py_path, to_snake_case(DEBUG_DIR)), exist_ok=True)
        os.makedirs(join(self.py_path, to_snake_case(DEBUG_DIR), to_snake_case(self.tool_policy.tool_name)), exist_ok=True)
        for item in self.tool_policy.policy_items:
            os.makedirs(join(self.py_path, to_snake_case(DEBUG_DIR), to_snake_case(self.tool_policy.tool_name), to_snake_case(item.name)), exist_ok=True)
        os.makedirs(join(self.py_path, to_snake_case(TESTS_DIR)), exist_ok=True)

    async def generate(self)->ToolGuardCodeResult:
        self.start()
        tool_guard_fn, item_guard_fns = self.create_initial_guard_fns()
        
        logger.debug(f"Tool {self.tool_policy.tool_name} function draft created")
    
        tests_and_guards = await asyncio.gather(* [
            self.generate_tool_item_tests_and_guard_fn(item, item_guard_fn)
                for item, item_guard_fn in zip(self.tool_policy.policy_items, item_guard_fns)
        ])
        item_tests, item_guards = zip(*tests_and_guards)
        return ToolGuardCodeResult(
            tool= self.tool_policy,
            guard_fn_name= guard_fn_name(self.tool_policy),
            guard_file= tool_guard_fn,
            item_guard_files = item_guards,
            test_files= item_tests
        )

    async def generate_tool_item_tests_and_guard_fn(self, item: ToolPolicyItem, init_guard_fn: FileTwin)->Tuple[FileTwin|None, FileTwin|None]:
        #1) Generate tests
        try:
            test_file = await self.generate_tool_item_tests(item, init_guard_fn)
        except Exception as ex:
            logger.warning("Tests generation failed.", ex)
            try:
                logger.warning("try to generate the code without tests...", ex)
                guard_fn = await self.improve_tool_item_guard_fn(init_guard_fn, [], item, 0)
                return None, guard_fn
            except Exception as ex:
                logger.warning("guard generation failed. return initial guard", ex)
                return None, init_guard_fn
        
        #2) Tests generated, now generate guards
        try:
            guard_fn = await self.improve_tool_item_guard_fn_loop(item, init_guard_fn, test_file)
            logger.debug(f"tool item generated successfully {item.name}") # 😄🎉 Happy path 
            return test_file, guard_fn
        except Exception as ex:
            logger.warning("guard generation failed. return initial guard", ex)
            return None, init_guard_fn

    async def generate_tool_item_tests(self, item: ToolPolicyItem, guard_fn: FileTwin)-> FileTwin:
        fn_name = guard_item_fn_name(item)
        dep_tools = set()
        if self.domain.app_api_size > 1:
            domain = Domain.model_construct(**self.domain.model_dump()) #remove runtime fields
            dep_tools = await tool_dependencies(item, domain)
        logger.debug(f"Dependencies of {item.name}: {dep_tools}")

        test_file_name = join(TESTS_DIR, self.tool_policy.tool_name, f"{test_fn_module_name(item)}.py")
        errors = []
        for trial_no in range(MAX_TEST_GEN_TRIALS):
            logger.debug(f"Generating tool {item.name} tests. iteration {trial_no}")
            first_time = trial_no == 0
            domain = Domain.model_construct(**self.domain.model_dump()) #remove runtime fields
            if first_time:
                res = await generate_tool_item_tests(fn_name, guard_fn, item, domain, dep_tools)
            else:
                res = await improve_tool_tests(test_file, domain, item, errors)

            test_content = res.get_code_content()
            test_file = FileTwin(
                file_name= test_file_name,
                content=test_content
            )
            test_file.save(self.py_path)
            test_file.save_as(self.py_path, self.debug_dir(item, f"{trial_no}_{test_fn_module_name(item)}.py"))

            lint_report = pyright.run(self.py_path, test_file.file_name, self.py_env)
            lint_report_filename =self.debug_dir(item, f"{trial_no}_{to_snake_case(item.name)}_pyright.json")
            report = FileTwin(
                file_name=lint_report_filename,
                content=lint_report.model_dump_json(indent=2)
            )
            report.save(self.py_path)

            if lint_report.summary.errorCount>0:
                logger.warning(f"Generated tests with {lint_report.summary.errorCount} Python errors {test_file.file_name}.")
                FileTwin(
                        file_name=self.debug_dir(item, f"{trial_no}_{test_fn_module_name(item)}_errors.json"), 
                        content=lint_report.model_dump_json(indent=2)
                    ).save(self.py_path, )
                errors = lint_report.list_error_messages()
                continue

            #syntax ok, try to run it...
            logger.debug(f"Generated Tests... (trial={trial_no})")
            report_file_name = self.debug_dir(item, f"{trial_no}_{to_snake_case(item.name)}_report.json")
            test_report = pytest.run(self.py_path, test_file.file_name, report_file_name)
            if test_report.all_tests_collected_successfully() and test_report.non_empty_tests():
                return test_file
            if not test_report.non_empty_tests():  # empty test set
                errors = ['empty set of generated unit tests is not allowed']
            else:
                errors = test_report.list_errors()
        
        raise Exception("Generated tests contain errors")
    
    async def improve_tool_item_guard_fn_loop(self, item: ToolPolicyItem, guard_fn: FileTwin, tests: FileTwin)->FileTwin:
        for trial_no in range(MAX_TOOL_IMPROVEMENTS):
            report_file_name = self.debug_dir(item, f"{trial_no}_{to_snake_case(item.name)}_report.json")
            errors = pytest.run(
                    self.py_path, 
                    tests.file_name,
                    report_file_name
                ).list_errors()
            if not errors: 
                return guard_fn
            
            logger.debug(f"Tool {item.name} guard function unit-tests failed. Retrying...")
            guard_fn = await self.improve_tool_item_guard_fn(guard_fn, errors, item, trial_no)
        
        raise Exception(f"Could not generate guard function for tool {to_snake_case(self.tool_policy.tool_name)}.{to_snake_case(item.name)}")

    async def improve_tool_item_guard_fn(self, prev_version: FileTwin, review_comments: List[str], item: ToolPolicyItem, round: int)->FileTwin:
        module_name = guard_item_fn_module_name(item)
        errors = []
        for trial in range(MAX_TOOL_IMPROVEMENTS):
            logger.debug(f"Improving guard function {module_name}... (trial = {round}.{trial})")
            domain = Domain.model_construct(**self.domain.model_dump()) #omit runtime fields
            prev_python = PythonCodeModel.create(python_code=prev_version.content)
            res = await improve_tool_guard_fn(prev_python, domain, item, review_comments + errors)

            guard_fn = FileTwin(
                file_name=prev_version.file_name,
                content=res.get_code_content()
            )
            guard_fn.save(self.py_path)
            guard_fn.save_as(self.py_path, self.debug_dir(item, f"{round}.{trial}_{module_name}.py"))

            lint_report = pyright.run(self.py_path, guard_fn.file_name, self.py_env)
            if lint_report.summary.errorCount>0:
                FileTwin(
                        file_name=self.debug_dir(item, f"{round}.{trial}_{module_name}_errors.json"), 
                        content=lint_report.model_dump_json(indent=2)
                    ).save(self.py_path, )
                logger.warning(f"Generated function {module_name} with {lint_report.summary.errorCount} errors.")
                
                errors = lint_report.list_error_messages()
                continue
            
            return guard_fn
        
        raise Exception(f"Generation failed for tool {item.name}")

    def create_initial_guard_fns(self)->Tuple[FileTwin, List[FileTwin]]:
        with py.temp_python_path(self.py_path):
            module = load_module_from_path(self.domain.app_api.file_name, self.py_path)
        assert module, f"File not found {self.domain.app_api.file_name}"
        cls = find_class_in_module(module, self.domain.app_api_class_name)
        tool_fn_name = to_snake_case(self.tool_policy.tool_name)
        tool_fn = getattr(cls, tool_fn_name)
        assert tool_fn, f"Function not found, {tool_fn_name}"

        #__init__.py
        path = join(to_snake_case(self.app_name), tool_fn_name, "__init__.py")
        FileTwin(file_name=path, content="").save(self.py_path)

        #item guards files
        item_files = [self._create_item_module(item, tool_fn) 
            for item in self.tool_policy.policy_items]
        #tool guard file
        tool_file = self._create_tool_module(tool_fn, item_files)

        #Save to debug folder
        for item_guard_fn, policy_item in zip(item_files, self.tool_policy.policy_items):
            item_guard_fn.save_as(self.py_path, self.debug_dir(policy_item, f"-1_{Path(item_guard_fn.file_name).parts[-1]}"))

        return (tool_file, item_files)
     
    def _create_tool_module(self, tool_fn: Callable, item_files:List[FileTwin])->FileTwin:
        file_name = join(
            to_snake_case(self.app_name), 
            to_snake_case(self.tool_policy.tool_name), 
            py.py_extension(
                guard_fn_module_name(self.tool_policy)
            )
        )
        items = [{
                "guard_fn": guard_item_fn_name(item),
                "file_name": file.file_name
            } for (item, file) in zip(self.tool_policy.policy_items, item_files)]
        sig = inspect.signature(tool_fn)
        sig_str = self.signature_str(sig)
        args_call = ", ".join([p for p in sig.parameters if p != "self"])
        args_doc_str = py.extract_docstr_args(tool_fn)
        return FileTwin(
            file_name=file_name,
            content=load_template("tool_guard.j2").render(
                domain = self.domain,
                method = {
                    "name": guard_fn_name(self.tool_policy),
                    "signature": sig_str,
                    "args_call": args_call,
                    "args_doc_str": args_doc_str
                },
                items=items
            )
        ).save(self.py_path)

    def signature_str(self, sig: inspect.Signature):
        sig_str = str(sig)
        sig_str = sig_str[sig_str.find("self,")+len("self,"): sig_str.rfind(")")].strip()
        return sig_str
    
    def _create_item_module(self, tool_item: ToolPolicyItem, tool_fn: Callable)->FileTwin:
        file_name = join(
            to_snake_case(self.app_name), 
            to_snake_case(self.tool_policy.tool_name), 
            py.py_extension(
                guard_item_fn_module_name(tool_item)
            )
        )
        sig_str = self.signature_str(inspect.signature(tool_fn))
        args_doc_str = py.extract_docstr_args(tool_fn)
        return FileTwin(
            file_name=file_name,
            content=load_template("tool_item_guard.j2").render(
                domain = self.domain,
                method = {
                    "name": guard_item_fn_name(tool_item),
                    "signature": sig_str,
                    "args_doc_str": args_doc_str
                },
                policy = tool_item.description
            )
        ).save(self.py_path)
    
    
    def debug_dir(self, policy_item: ToolPolicyItem, dir:str):
        return join(DEBUG_DIR, to_snake_case(self.tool_policy.tool_name), to_snake_case(policy_item.name), dir)
