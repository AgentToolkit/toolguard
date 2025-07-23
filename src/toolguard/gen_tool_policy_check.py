import asyncio
import inspect
import os
from os.path import join
from typing import Any, Callable, List, Optional, Tuple
from loguru import logger
from toolguard.common.array import find
from toolguard.common import py
from toolguard.common.str import to_camel_case, to_snake_case
from toolguard.gen_domain import OpenAPICodeGenerator
import toolguard.prompts as prompts
from toolguard.data_types import Domain, FileTwin, ToolPolicy, ToolPolicyItem, ToolPolicyItem
from toolguard.py_to_oas import tools_to_openapi
from toolguard.runtime import ToolGuardsCodeGenerationResult, ToolGuardCodeResult, find_class_in_module, load_module_from_path
from toolguard.templates import load_template
import toolguard.utils.pyright as pyright
import toolguard.utils.pytest as pytest
from toolguard.llm_utils import post_process_llm_response

import asyncio
from pathlib import Path
from typing import List
from loguru import logger
from toolguard.data_types import FileTwin, ToolPolicy
import toolguard.utils.venv as venv
import toolguard.utils.pyright as pyright


MAX_TOOL_IMPROVEMENTS = 5
MAX_TEST_GEN_TRIALS = 3
PY_ENV = "my_env"
PY_PACKAGES = ["pydantic", "pytest"]#, "litellm"]
DEBUG_DIR = "debug"
TESTS_DIR = "tests"
HISTORY_PARAM = "history"
HISTORY_PARAM_TYPE = "ChatHistory"
API_PARAM = "api"


async def generate_tools_check_fns(app_name: str, tool_policies: List[ToolPolicy], py_root:str, funcs: List[Callable])->ToolGuardsCodeGenerationResult:
    logger.debug(f"Starting... will save into {py_root}")

    #Open API Spec is the common way to specify API
    oas = tools_to_openapi(app_name, funcs)
    openapi_path = join(py_root, f"{app_name}_oas.json")
    oas.save(openapi_path)

    #Domain from Open API Spec
    domain = OpenAPICodeGenerator(py_root, app_name).generate_domain(openapi_path, funcs)
    
    #Setup env (slow, hence last):
    venv.run(join(py_root, PY_ENV), PY_PACKAGES)
    pyright.config(py_root)
    pytest.configure(py_root)
    
    #tools
    tools_w_poilicies = [tool_policy for tool_policy in tool_policies if len(tool_policy.policy_items) > 0]
    #tools_w_poilicies = [tool_policy for tool_policy in tool_policies ]
    tool_results = await asyncio.gather(*[
        ToolCheckPolicyGenerator(app_name, tool, py_root, domain).generate()
        for tool in tools_w_poilicies
    ])


    tools_result = {tool.name:res 
        for tool, res 
        in zip(tools_w_poilicies, tool_results)
    }        
    return ToolGuardsCodeGenerationResult(
        domain=domain,
        tools=tools_result
    ).save(py_root)

class ToolCheckPolicyGenerator:
    app_name: str
    py_path: str
    app_path: str
    tool: ToolPolicy
    domain: Domain
    common: FileTwin

    def __init__(self, app_name:str, tool:ToolPolicy, py_path:str, domain:Domain) -> None:
        self.py_path = py_path
        self.app_name = app_name
        self.tool = tool
        self.domain = domain
        self.app_path = join(py_path, to_snake_case(app_name))
        os.makedirs(self.app_path, exist_ok=True)
        os.makedirs(join(self.app_path, to_snake_case(tool.name)), exist_ok=True)
        os.makedirs(join(py_path, to_snake_case(DEBUG_DIR)), exist_ok=True)
        os.makedirs(join(py_path, to_snake_case(DEBUG_DIR), to_snake_case(self.tool.name)), exist_ok=True)
        os.makedirs(join(py_path, to_snake_case(TESTS_DIR)), exist_ok=True)

    async def generate(self)->ToolGuardCodeResult:
        tool_check_fn, item_check_fns = self.create_initial_check_fns()
        for item_check_fn in item_check_fns:
            item_check_fn.save_as(self.py_path, self.debug_dir(f"-1_{Path(item_check_fn.file_name).parts[-1]}"))
        
        logger.debug(f"Tool {self.tool.name} function draft created")
    
        items_tests = await asyncio.gather(* [
            self.generate_tool_item_tests_and_check_fn(item, item_check_fn)
                for item, item_check_fn in zip(self.tool.policy_items, item_check_fns)
        ])
        return ToolGuardCodeResult(
            tool=self.tool,
            guard_fn_name=self.guard_fn_name(),
            guard_file=tool_check_fn,
            item_guard_files = item_check_fns,
            test_files=items_tests
        )

    async def generate_tool_item_tests_and_check_fn(self, item: ToolPolicyItem, check_fn: FileTwin)->FileTwin|None:
        try:
            tests = await self.generate_tool_item_tests(item, check_fn)
            await self.improve_tool_item_check_fn_loop(item, check_fn, tests)
            return tests
        except Exception as ex:
            logger.error(ex)
            return None

    async def generate_tool_item_tests(self, item: ToolPolicyItem, check_fn: FileTwin)-> FileTwin:
        fn_name = self.guard_item_fn_name(item)
        dep_tools = await prompts.tool_information_dependencies(item.name, item.description, self.domain.api)
        dep_tools = set(dep_tools) #workaround. generative AI
        logger.debug(f"Dependencies of {item.name}: {dep_tools}")

        test_file_name = join(TESTS_DIR, self.tool.name, f"{self.test_fn_module_name(item)}.py")
        errors = []
        for trial_no in range(MAX_TEST_GEN_TRIALS):
            logger.debug(f"Generating tool {item.name} tests. iteration {trial_no}")
            first_time = trial_no == 0
            if first_time:
                res_content = await prompts.generate_tool_item_tests(fn_name, check_fn, item, self.domain.common, self.domain.api, dep_tools)
            else:
                res_content = await prompts.improve_tool_tests(test_file, self.domain.api, self.domain.common, item, errors) # type: ignore #

            test_content = post_process_llm_response(res_content)
            test_file = FileTwin(
                file_name= test_file_name,
                content=test_content
            )
            test_file.save(self.py_path)
            test_file.save_as(self.py_path, self.debug_dir(f"{trial_no}_{self.test_fn_module_name(item)}.py"))

            lint_report = pyright.run(self.py_path, test_file.file_name, PY_ENV)
            lint_report_filename =self.debug_dir(f"{trial_no}_{to_snake_case(item.name)}_pyright.json")
            report = FileTwin(
                file_name=lint_report_filename,
                content=lint_report.model_dump_json(indent=2)
            )
            report.save(self.py_path)

            if lint_report.summary.errorCount>0:
                logger.warning(f"Generated tests with {lint_report.summary.errorCount} Python errors {test_file.file_name}.")
                FileTwin(
                        file_name=self.debug_dir(f"{trial_no}_{self.test_fn_module_name(item)}_errors.json"), 
                        content=lint_report.model_dump_json(indent=2)
                    ).save(self.py_path, )
                errors = lint_report.list_error_messages()
                continue

            #syntax ok, try to run it...
            logger.debug(f"Generated Tests... (trial={trial_no})")
            report_file_name = self.debug_dir(f"{trial_no}_{to_snake_case(item.name)}_report.json")
            test_report = pytest.run(self.py_path, test_file.file_name, report_file_name)
            if test_report.all_tests_collected_successfully() and test_report.non_empty_tests():
                return test_file
            if not test_report.non_empty_tests():  # empty test set
                errors = ['empty set of generated unit tests is not allowed']
            else:
                errors = test_report.list_errors()
        
        raise Exception("Generated tests contain errors")
    
    async def improve_tool_item_check_fn_loop(self, item: ToolPolicyItem, check_fn: FileTwin, tests:FileTwin)->FileTwin:
        for trial_no in range(MAX_TOOL_IMPROVEMENTS):
            report_file_name = self.debug_dir(f"{trial_no}_{to_snake_case(item.name)}_report.json")
            errors = pytest.run(
                    self.py_path, 
                    tests.file_name,
                    report_file_name
                ).list_errors()
            if not errors: 
                return check_fn
            
            logger.debug(f"Tool {item.name} check function unit-tests failed. Retrying...")
            check_fn = await self.improve_check_fn(check_fn, errors, item)
        
        raise Exception(f"Could not generate check function for tool {item.name}")

    async def improve_check_fn(self, prev_version:FileTwin, review_comments: List[str], item: ToolPolicyItem)->FileTwin:
        module_name = self.guard_item_fn_module_name(item)
        errors = []
        for trial in range(MAX_TOOL_IMPROVEMENTS):
            logger.debug(f"Improving check function {module_name}... (trial = {trial})")
            res_content = await prompts.improve_tool_check_fn(prev_version, self.domain.common, self.domain.api, item, review_comments + errors)

            body = post_process_llm_response(res_content)
            check_fn = FileTwin(
                file_name=prev_version.file_name,
                content=body
            )
            check_fn.save(self.py_path)
            check_fn.save_as(self.py_path, self.debug_dir(f"{trial}_{module_name}.py"))

            lint_report = pyright.run(self.py_path, check_fn.file_name, PY_ENV)
            if lint_report.summary.errorCount>0:
                FileTwin(
                        file_name=self.debug_dir(f"{trial}_{module_name}_errors.json"), 
                        content=lint_report.model_dump_json(indent=2)
                    ).save(self.py_path, )
                logger.warning(f"Generated function {module_name} with {lint_report.summary.errorCount} errors.")
                
                errors = lint_report.list_error_messages()
                continue
            
            return check_fn
        
        raise Exception(f"Generation failed for tool {item.name}")

    def create_initial_check_fns(self)->Tuple[FileTwin, List[FileTwin]]:
        with py.temp_python_path(self.py_path):
            print(self.domain.api.file_name)
            print( self.py_path)
            module = load_module_from_path(self.domain.api.file_name, self.py_path)
        assert module, f"File not found {self.domain.api.file_name}"
        cls = find_class_in_module(module, self.domain.api_class_name)
        tool_fn = getattr(cls, to_camel_case(self.tool.name))
        assert tool_fn, f"Function not found, {to_camel_case(self.tool.name)}"
        sig = inspect.signature(tool_fn)
        param = find(list(sig.parameters.values()), lambda prm: prm.name != "self")
        assert param

        #__init__.py
        path = join(to_snake_case(self.app_name), to_snake_case(self.tool.name), "__init__.py")
        FileTwin(file_name=path, content="").save(self.py_path)

        arg = {
            "name": param.name,
            "type": param.annotation.__name__
        }
        #item guards files
        item_files = [self._create_item_module(item, arg) 
            for item in self.tool.policy_items]
        #tool guard file
        tool_file = self._create_tool_module(arg, item_files)

        return (tool_file, item_files)
     
    def _create_tool_module(self, arg: dict, item_files:List[FileTwin])->FileTwin:
        file_name = join(
            to_snake_case(self.app_name), 
            to_snake_case(self.tool.name), 
            py.py_extension(
                self.guard_fn_module_name()
            )
        )
        items = [{
                "guard_fn": self.guard_item_fn_name(item),
                "file_name": file.file_name
            } for (item, file) in zip(self.tool.policy_items, item_files)]
        return FileTwin(
            file_name=file_name,
            content=load_template("tool_guard.j2").render(
                domain = self.domain,
                method = {
                    "name": self.guard_fn_name(),
                    "arg": arg
                },
                items=items
            )
        ).save(self.py_path)
    
    def _create_item_module(self, tool_item: ToolPolicyItem, arg: dict)->FileTwin:
        file_name = join(
            to_snake_case(self.app_name), 
            to_snake_case(self.tool.name), 
            py.py_extension(
                self.guard_item_fn_module_name(tool_item)
            )
        )
        return FileTwin(
            file_name=file_name,
            content=load_template("tool_item_guard.j2").render(
                domain = self.domain,
                method = {
                    "name": self.guard_item_fn_name(tool_item),
                    "arg": arg
                },
                policy = tool_item.description
            )
        ).save(self.py_path)
    
    def debug_dir(self, dir:str):
        return join(DEBUG_DIR, to_snake_case(self.tool.name), dir)
    
    def guard_fn_name(self)->str:
        return to_snake_case(f"guard_{self.tool.name}")

    def guard_fn_module_name(self)->str:
        return to_snake_case(f"guard_{self.tool.name}")

    def guard_item_fn_name(self, tool_item: ToolPolicyItem)->str:
        return to_snake_case(f"guard_{tool_item.name}")

    def guard_item_fn_module_name(self, tool_item: ToolPolicyItem)->str:
        return to_snake_case(f"guard_{tool_item.name}")

    def test_fn_name(self, tool_item: ToolPolicyItem)->str:
        return to_snake_case(f"test_guard_{tool_item.name}")

    def test_fn_module_name(self, tool_item:ToolPolicyItem)->str:
        return to_snake_case(f"test_guard_{tool_item.name}")