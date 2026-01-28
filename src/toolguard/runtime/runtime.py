import importlib
import inspect
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Awaitable, Callable, Dict, Optional, Type

from pydantic import BaseModel

from toolguard.runtime import IToolInvoker
from toolguard.runtime.data_types import (
    API_PARAM,
    ARGS_PARAM,
    RESULTS_FILENAME,
    ToolGuardsCodeGenerationResult,
)


def load_toolguards(
    directory: str | Path, filename: str | Path = RESULTS_FILENAME
) -> "ToolguardRuntime":
    """Load toolguards from a directory.

    Args:
        directory: The directory containing the toolguard files.
        filename: The name of the results file to load. Defaults to RESULTS_FILENAME.

    Returns:
        ToolguardRuntime: A runtime instance for executing toolguards.
    """
    return ToolguardRuntime(
        ToolGuardsCodeGenerationResult.load(directory, filename), Path(directory)
    )


class ToolguardRuntime:
    """Runtime environment for executing toolguards.

    This class manages the lifecycle of toolguard execution, including:
    - Loading and caching guard functions
    - Managing Python path modifications
    - Coordinating guard function calls with proper argument injection
    """

    _original_pypath: list[str] = []

    def __init__(self, result: ToolGuardsCodeGenerationResult, ctx_dir: Path) -> None:
        self._ctx_dir = ctx_dir
        self._result = result

    def __enter__(self):
        # add folder to python path
        self._original_pypath = list(sys.path)  # remember old path
        sys.path.insert(0, os.path.abspath(self._ctx_dir))

        # cache the tool guards
        self._guards: Dict[str, Callable[..., Awaitable[Any]]] = {}
        for tool_name, tool_result in self._result.tools.items():
            mod_name = _file_to_module_name(tool_result.guard_file.file_name)
            module = importlib.import_module(mod_name)
            guard_fn = _find_function_in_module(module, tool_result.guard_fn_name)
            assert guard_fn, "Guard not found"
            self._guards[tool_name] = guard_fn

        return self

    def __exit__(self, exc_type, exc, tb):
        del self._guards
        # back to original python path
        sys.path[:] = self._original_pypath
        return False

    def _make_args(
        self, guard_fn: Callable, args: dict, delegate: IToolInvoker
    ) -> Dict[str, Any]:
        sig = inspect.signature(guard_fn)
        guard_args = {}
        for p_name, param in sig.parameters.items():
            if p_name == API_PARAM:
                mod_name = _file_to_module_name(
                    self._result.domain.app_api_impl.file_name
                )
                module = importlib.import_module(mod_name)
                clazz = _find_class_in_module(
                    module, self._result.domain.app_api_impl_class_name
                )
                assert clazz, (
                    f"class {self._result.domain.app_api_impl_class_name} not found in {self._result.domain.app_api_impl.file_name}"
                )
                guard_args[p_name] = clazz(delegate)
            else:
                arg_val = args.get(p_name)
                if arg_val is None and p_name == ARGS_PARAM:
                    arg_val = args

                if inspect.isclass(param.annotation) and issubclass(
                    param.annotation, BaseModel
                ):
                    guard_args[p_name] = param.annotation.model_construct(**arg_val)
                else:
                    guard_args[p_name] = arg_val
        return guard_args

    async def guard_toolcall(self, tool_name: str, args: dict, delegate: IToolInvoker):
        """Execute a guard function for a specific tool call.

        Args:
            tool_name: The name of the tool being invoked.
            args: Dictionary of arguments to pass to the tool.
            delegate: The tool invoker instance for executing the actual tool.

        Raises:
            PolicyViolationException: If the guard function detects a policy violation.
        """
        guard_fn = self._guards.get(tool_name)
        if guard_fn is None:  # No guard assigned to this tool
            return
        await guard_fn(**self._make_args(guard_fn, args, delegate))


def _file_to_module_name(file_path: str | Path):
    return str(file_path).removesuffix(".py").replace("/", ".")


def _find_function_in_module(module: ModuleType, function_name: str):
    func = getattr(module, function_name, None)
    if func is None or not inspect.isfunction(func):
        raise AttributeError(
            f"Function '{function_name}' not found in module '{module.__name__}'"
        )
    return func


def _find_class_in_module(module: ModuleType, class_name: str) -> Optional[Type]:
    cls = getattr(module, class_name, None)
    if isinstance(cls, type):
        return cls
    return None
