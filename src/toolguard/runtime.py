import importlib
import inspect
import json
import os
import sys
from types import ModuleType
from typing import Any, Dict, List, Optional, Type, Callable, TypeVar
from pydantic import BaseModel
from langchain_core.tools import BaseTool

import functools
from .data_types import API_PARAM, ARGS_PARAM, RESULTS_FILENAME, FileTwin, RuntimeDomain, ToolGuardSpec

from abc import ABC, abstractmethod


class IToolInvoker(ABC):
    T = TypeVar("T")

    @abstractmethod
    def invoke(
        self, toolname: str, arguments: Dict[str, Any], return_type: Type[T]
    ) -> T: ...

def load_toolguard_code_result(directory: str, filename: str = RESULTS_FILENAME):
    full_path = os.path.join(directory, filename)
    with open(full_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ToolGuardsCodeGenerationResult(**data)

def load_toolguards(directory: str, filename: str = RESULTS_FILENAME) -> "ToolguardRuntime":
    return ToolguardRuntime(load_toolguard_code_result(directory, filename), directory)

class ToolGuardCodeResult(BaseModel):
    tool: ToolGuardSpec
    guard_fn_name: str
    guard_file: FileTwin
    item_guard_files: List[FileTwin | None]
    test_files: List[FileTwin | None]


class ToolGuardsCodeGenerationResult(BaseModel):
    out_dir: str
    domain: RuntimeDomain
    tools: Dict[str, ToolGuardCodeResult]

    def save(
        self, directory: str, filename: str = RESULTS_FILENAME
    ) -> "ToolGuardsCodeGenerationResult":
        full_path = os.path.join(directory, filename)
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2)
        return self


class ToolguardRuntime:
    _original_pypath:list[str] = []

    def __init__(self, result: ToolGuardsCodeGenerationResult, ctx_dir: str) -> None:
        self._ctx_dir = ctx_dir
        self._result = result

    def __enter__(self):
        #add folder to python path
        self._original_pypath = list(sys.path) #remember old path
        sys.path.insert(0, os.path.abspath(self._ctx_dir))

        #cache the tool guards
        self._guards = {}
        for tool_name, tool_result in self._result.tools.items():
            mod_name = file_to_module_name(tool_result.guard_file.file_name)
            module = importlib.import_module(mod_name)
            guard_fn = find_function_in_module(module, tool_result.guard_fn_name)
            assert guard_fn, "Guard not found"
            self._guards[tool_name] = guard_fn

        return self

    def __exit__(self, exc_type, exc, tb):
        del self._guards
        #back to original python path
        sys.path[:] = self._original_pypath
        return False
    
    def _make_args(self, guard_fn:Callable, args: dict,  delegate: IToolInvoker)->Dict[str, Any]:
        sig = inspect.signature(guard_fn)
        guard_args = {}
        for p_name, param in sig.parameters.items():
            if p_name == API_PARAM:
                mod_name = file_to_module_name(self._result.domain.app_api_impl.file_name)
                module = importlib.import_module(mod_name)
                clazz = find_class_in_module(module, self._result.domain.app_api_impl_class_name)
                assert clazz, f"class {self._result.domain.app_api_impl_class_name} not found in {self._result.domain.app_api_impl.file_name}"
                guard_args[p_name] = clazz(delegate)
            else:
                arg_val = args.get(p_name)
                if arg_val is None and p_name == ARGS_PARAM:
                    arg_val = args
                
                if inspect.isclass(param.annotation) and issubclass(param.annotation, BaseModel):
                    guard_args[p_name] = param.annotation.model_construct(**arg_val)
                else:
                    guard_args[p_name] = arg_val
        return guard_args

    def check_toolcall(self, tool_name: str, args: dict, delegate: IToolInvoker):
        guard_fn = self._guards.get(tool_name)
        if guard_fn is None:  # No guard assigned to this tool
            return
        guard_fn(**self._make_args(guard_fn, args, delegate))

def file_to_module_name(file_path:str):
    return file_path.removesuffix('.py').replace('/', '.')

def find_function_in_module(module: ModuleType, function_name: str):
    func = getattr(module, function_name, None)
    if func is None or not inspect.isfunction(func):
        raise AttributeError(
            f"Function '{function_name}' not found in module '{module.__name__}'"
        )
    return func


def find_class_in_module(module: ModuleType, class_name: str) -> Optional[Type]:
    cls = getattr(module, class_name, None)
    if isinstance(cls, type):
        return cls
    return None


T = TypeVar("T")


def guard_methods(obj: T, guards_folder: str) -> T:
    """Wraps all public bound methods of the given instance using the given wrapper."""
    for attr_name in dir(obj):
        if attr_name.startswith("_"):
            continue
        attr = getattr(obj, attr_name)
        if callable(attr):
            wrapped = guard_before_call(guards_folder)(attr)
            setattr(obj, attr_name, wrapped)
    return obj


class ToolMethodsInvoker(IToolInvoker):
    def __init__(self, object: object) -> None:
        self._obj = object

    def invoke(self, toolname: str, arguments: Dict[str, Any], return_type: Type[T]) -> T:
        mtd = getattr(self._obj, toolname)
        assert callable(mtd), f"Tool {toolname} was not found"
        return mtd(**arguments)


class ToolFunctionsInvoker(IToolInvoker):
    def __init__(self, funcs: List[Callable]) -> None:
        self._funcs_by_name = {func.__name__: func for func in funcs}

    def invoke(self, toolname: str, arguments: Dict[str, Any], return_type: Type[T]) -> T:
        func = self._funcs_by_name.get(toolname)
        assert callable(func), f"Tool {toolname} was not found"
        return func(**arguments)

class LangchainToolInvoker(IToolInvoker):
    T = TypeVar("T")
    _tools: Dict[str, BaseTool]

    def __init__(self, tools: List[BaseTool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def invoke(self, toolname: str, arguments: Dict[str, Any], return_type: Type[T])->T:
        tool = self._tools.get(toolname)
        if tool:
            return tool.invoke(arguments)
        raise ValueError(f"unknown tool {toolname}")
    
def guard_before_call(guards_folder: str) -> Callable[[Callable], Callable]:
    """Decorator factory that logs function calls to the given logfile."""
    toolguards = load_toolguards(guards_folder)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            toolguards.check_toolcall(
                func.__name__, kwargs, ToolMethodsInvoker(func.__self__)
            )
            return func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator
