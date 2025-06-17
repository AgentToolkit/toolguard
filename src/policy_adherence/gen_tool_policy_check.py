import ast
import asyncio
import copy
import os
import time
from os.path import join
from typing import Any, List, Tuple
from loguru import logger
from policy_adherence.common.array import find
from policy_adherence.common import py
from policy_adherence.common.str import to_snake_case
from policy_adherence.gen_domain import OpenAPICodeGenerator
import policy_adherence.prompts as prompts
from policy_adherence.data_types import FileTwin, ToolChecksCodeResult, ToolPolicy, ToolPolicyItem, ToolPolicyItem
import policy_adherence.utils.pyright as pyright
import policy_adherence.utils.pytest as pytest
from policy_adherence.llm_utils import post_process_llm_response

import asyncio
from pathlib import Path
from typing import List
from loguru import logger
from policy_adherence.data_types import FileTwin, ToolChecksCodeGenerationResult, ToolPolicy
import policy_adherence.utils.venv as venv
import policy_adherence.utils.pyright as pyright


MAX_TOOL_IMPROVEMENTS = 5
MAX_TEST_GEN_TRIALS = 3
PY_ENV = "my_env"
PY_PACKAGES = ["pydantic", "pytest"]#, "litellm"]
DEBUG_DIR = "debug"
TESTS_DIR = "tests"
RUNTIME_COMMON_PY = "common.py"
DOMAIN_PY = "domain.py"
HISTORY_PARAM = "history"
HISTORY_PARAM_TYPE = "ChatHistory"
API_PARAM = "api"

def check_fn_name(name:str)->str:
    return to_snake_case(f"guard_{name}")

def check_fn_module_name(name:str)->str:
    return to_snake_case(check_fn_name(name))

def test_fn_name(name:str)->str:
    return to_snake_case(f"test_guard_{name}")

def test_fn_module_name(name:str)->str:
    return to_snake_case(test_fn_name(name))

def get_annotation_str(annotation):
    if annotation is None:
        return "unannotated"
    elif isinstance(annotation, ast.Name):
        return annotation.id
    elif isinstance(annotation, ast.Subscript):
        return ast.unparse(annotation)  # Python 3.9+
    elif isinstance(annotation, ast.Attribute):
        return ast.unparse(annotation)
    else:
        return "unknown"
    
def fn_doc_string(args: list[ast.arg], history_arg, api_arg):
    app_args_doc = "\n    ".join([f"{arg.arg} ({get_annotation_str(arg.annotation)})" for arg in args])
    
    def add_policy(policy:str):
        return f"""
Checks that a tool call complies with the following policy:
>{policy}

Args:
    {app_args_doc}
    {history_arg.arg} ({history_arg.annotation.id}): provide question-answer services over the past chat messages.
    {api_arg.arg} ({api_arg.annotation.id}): api to access other tools.

Raises:
    PolicyViolationException: If the request violates the policy.
"""
    return add_policy
    

async def generate_tools_check_fns(app_name: str, tools: List[ToolPolicy], py_root:str, openapi_path:str)->ToolChecksCodeGenerationResult:
    logger.debug(f"Starting... will save into {py_root}")

    #Setup:
    venv.run(join(py_root, PY_ENV), PY_PACKAGES)
    pyright.config(py_root)
    pytest.configure(py_root)

    #app folder:
    app_root = join(py_root, app_name)
    os.makedirs(app_root, exist_ok=True)
    py.create_init_py(app_root)

    #common
    tmp_common = FileTwin.load_from(str(Path(__file__).parent), "_runtime_common.py")
    tmp_common.save_as(py_root, join(app_name, RUNTIME_COMMON_PY))

    # domain
    domain = OpenAPICodeGenerator(app_root)\
        .generate_domain(openapi_path, DOMAIN_PY)
    
    #tools
    tools_w_poilicies = [tool for tool in tools if len(tool.policy_items) > 0]
    tool_results = await asyncio.gather(*[
        ToolCheckPolicyGenerator(app_name, tool, py_root).generate()
        for tool in tools_w_poilicies
    ])
    
    tools_result = {tool.name:res 
        for tool, res 
        in zip(tools_w_poilicies, tool_results)
    }        
    return ToolChecksCodeGenerationResult(
        output_path=py_root,
        domain_file=domain.file_name,
        tools=tools_result
    )

class ToolCheckPolicyGenerator:
    app_name: str
    py_path:str
    tool:ToolPolicy
    domain: FileTwin
    common:FileTwin

    def __init__(self, app_name:str, tool:ToolPolicy, py_path:str) -> None:
        self.py_path = py_path
        self.app_name = app_name
        self.tool = tool
        self.domain = FileTwin.load_from(py_path, join(app_name, DOMAIN_PY))
        self.common = FileTwin.load_from(py_path, join(app_name, RUNTIME_COMMON_PY))
        os.makedirs(join(py_path, to_snake_case(app_name), to_snake_case(tool.name)), exist_ok=True)
        os.makedirs(join(py_path, to_snake_case(DEBUG_DIR)), exist_ok=True)
        os.makedirs(join(py_path, to_snake_case(TESTS_DIR)), exist_ok=True)

    async def generate(self)->ToolChecksCodeResult:
        tool_check_fn, item_check_fns = self.create_initial_check_fns()
        for item_check_fn in item_check_fns:
            item_check_fn.save_as(self.py_path, join(DEBUG_DIR, f"-1_{Path(item_check_fn.file_name).parts[-1]}"))
        
        logger.debug(f"Tool {self.tool.name} function draft created")
    
        items_tests = await asyncio.gather(* [
            self.generate_tool_item_tests_and_check_fn(item, item_check_fn)
                for item, item_check_fn in zip(self.tool.policy_items, item_check_fns)
        ])
        return ToolChecksCodeResult(
            tool=self.tool,
            tool_check_file=tool_check_fn,
            item_check_files = item_check_fns,
            test_files=items_tests
        )

    async def generate_tool_item_tests_and_check_fn(self, item: ToolPolicyItem, check_fn: FileTwin)->FileTwin|None:
        try:
            time.sleep(10)
            tests = await self.generate_tool_item_tests(item, check_fn)
            await self.improve_tool_item_check_fn_loop(item, check_fn, tests)
            return tests
        except Exception as ex:
            logger.error(ex)
            return None

    async def generate_tool_item_tests(self, item: ToolPolicyItem, check_fn: FileTwin)-> FileTwin:
        fn_name = check_fn_name(item.name)
        dep_tools = await prompts.tool_information_dependencies(item.name, item.description, self.domain)
        dep_tools = set(dep_tools) #workaround. generative AI
        logger.debug(f"Dependencies of {item.name}: {dep_tools}")

        test_file_name = join(TESTS_DIR, self.tool.name, f"{test_fn_module_name(item.name)}.py")
        errors = []
        for trial_no in range(MAX_TEST_GEN_TRIALS):
            logger.debug(f"Generating tool {item.name} tests. iteration {trial_no}")
            first_time = trial_no == 0
            if first_time:
                res_content = await prompts.generate_tool_item_tests(fn_name, check_fn, item, self.common, self.domain, dep_tools)
            else:
                res_content = await prompts.improve_tool_tests(test_file, self.domain, item, errors)

            test_content = post_process_llm_response(res_content)
            test_file = FileTwin(
                file_name= test_file_name,
                content=test_content
            )
            test_file.save(self.py_path)
            test_file.save_as(self.py_path, join(DEBUG_DIR, f"{trial_no}_{test_fn_module_name(item.name)}.py"))

            lint_report = pyright.run(self.py_path, test_file.file_name, PY_ENV)
            lint_report_filename = join(DEBUG_DIR, f"{trial_no}_{to_snake_case(item.name)}_pyright.json")
            report = FileTwin(
                file_name=lint_report_filename,
                content=lint_report.model_dump_json(indent=2)
            )
            report.save(self.py_path)

            if lint_report.summary.errorCount>0:
                logger.warning(f"Generated tests with {lint_report.summary.errorCount} Python errors {test_file.file_name}.")
                FileTwin(
                        file_name=join(DEBUG_DIR, f"{trial_no}_{test_fn_module_name(item.name)}_errors.json"), 
                        content=lint_report.model_dump_json(indent=2)
                    ).save(self.py_path, )
                errors = lint_report.list_error_messages()
                continue

            #syntax ok, try to run it...
            logger.debug(f"Generated Tests... (trial={trial_no})")
            report_file_name = join(DEBUG_DIR, f"{trial_no}_{to_snake_case(item.name)}_report.json")
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
            report_file_name = join(DEBUG_DIR, f"{trial_no}_{to_snake_case(item.name)}_report.json")
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
        module_name = check_fn_module_name(item.name)
        errors = []
        for trial in range(MAX_TOOL_IMPROVEMENTS):
            logger.debug(f"Improving check function {module_name}... (trial = {trial})")
            res_content = await prompts.improve_tool_check_fn(prev_version, self.domain, item, review_comments + errors)

            body = post_process_llm_response(res_content)
            check_fn = FileTwin(
                file_name=prev_version.file_name,
                content=body
            )
            check_fn.save(self.py_path)
            check_fn.save_as(self.py_path, join(DEBUG_DIR, f"{trial}_{module_name}.py"))

            lint_report = pyright.run(self.py_path, check_fn.file_name, PY_ENV)
            if lint_report.summary.errorCount>0:
                FileTwin(
                        file_name=join(DEBUG_DIR, f"{trial}_{module_name}_errors.json"), 
                        content=lint_report.model_dump_json(indent=2)
                    ).save(self.py_path, )
                logger.warning(f"Generated function {module_name} with {lint_report.summary.errorCount} errors.")
                
                errors = lint_report.list_error_messages()
                continue
            
            return check_fn
        
        raise Exception(f"Generation failed for tool {item.name}")
    
    def find_api_class(self, nodes: List[Any])->ast.ClassDef:
        for node in nodes:
            if isinstance(node, ast.ClassDef):
                if find(node.bases, lambda base: isinstance(base, ast.Name) and base.id == "Protocol"):
                    return node
                
    def find_tool_method(self, clz:ast.ClassDef, tool_name: str)->ast.FunctionDef:
        for fn in clz.body:
            if isinstance(fn, ast.FunctionDef):
                if fn.name == to_snake_case(tool_name):
                    return fn

    def create_initial_check_fns(self)->Tuple[FileTwin, List[FileTwin]]:
        tree = ast.parse(self.domain.content)
        api_cls = self.find_api_class(tree.body)
        assert api_cls
        tool_fn = self.find_tool_method(api_cls, self.tool.name)
        assert tool_fn

        fn_args:ast.arguments = tool_fn.args # type: ignore
        
        #remove self arg
        if fn_args.args:
            if fn_args.args[0].arg == "self":
                fn_args.args.pop(0)
        args = copy.deepcopy(fn_args.args)
        history_arg = ast.arg(arg=HISTORY_PARAM, annotation=ast.Name(id=HISTORY_PARAM_TYPE, ctx=ast.Load()))
        api_arg = ast.arg(arg=API_PARAM, annotation=ast.Name(id=api_cls.name, ctx=ast.Load()))
        
        docstring_fn = fn_doc_string(args, history_arg, api_arg)
        fn_args.args.extend([history_arg, api_arg])

        py.create_init_py(join(self.py_path, to_snake_case(self.app_name), to_snake_case(self.tool.name)))
        
        item_files = [self._create_item_module(item, fn_args, docstring_fn(item.description)) 
            for item in self.tool.policy_items]
        
        body = [
            py.create_import(py.py_module(self.domain.file_name), "*"),
            py.create_import(py.py_module(self.common.file_name), "*")
        ]
        for item_module, item in zip(item_files, self.tool.policy_items):
            body.append(py.create_import(
                py.py_module(item_module.file_name),
                check_fn_name(item.name)
            ))
        
        fn_body = [ast.Expr(value=ast.Constant(value=docstring_fn(self.tool.name), kind=None))]
        for item in self.tool.policy_items:
            params = [arg.arg for arg in args]+[HISTORY_PARAM, API_PARAM]
            fn_body.append(
                py.call_fn(check_fn_name(item.name), *params) 
            )
        body.append(py.create_fn(
            name=check_fn_name(self.tool.name),
            args=fn_args,
            body=fn_body
        )) # type: ignore
        file_name = join(
            to_snake_case(self.app_name),
            to_snake_case(self.tool.name),
            py.py_extension(check_fn_module_name(self.tool.name))
        )
        tool_file = py.save_py_body(body, file_name, self.py_path)
        return (tool_file, item_files)
     

    def _create_item_module(self, tool_item: ToolPolicyItem, fn_args:ast.arguments, fn_docstring:str)->FileTwin:
        body = [
            py.create_import(f"{py.py_module(self.domain.file_name)}", "*"),
            py.create_import(f"{py.py_module(self.common.file_name)}", "*"),
            py.create_fn(
                name=check_fn_name(tool_item.name), 
                args=fn_args,
                body=[ast.Expr(value=ast.Constant(value=fn_docstring, kind=None))]
            )
        ]
        file_name = join(
            to_snake_case(self.app_name), 
            to_snake_case(self.tool.name), 
            py.py_extension(
                check_fn_module_name(tool_item.name)
            )
        )
        return py.save_py_body(body, file_name, self.py_path)
