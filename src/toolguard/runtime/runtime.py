import importlib
import importlib.util
import inspect
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Awaitable, Callable, Dict, List, Optional, Type

from pydantic import BaseModel

from toolguard.runtime import IToolInvoker
from toolguard.runtime.data_types import (
    API_PARAM,
    ARGS_PARAM,
    RESULTS_FILENAME,
    FileTwin,
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
        ToolGuardsCodeGenerationResult.load(directory, filename),
        ctx_dir=Path(directory),
        file_twins=None,
    )


def load_toolguards_from_memory(
    result: ToolGuardsCodeGenerationResult,
) -> "ToolguardRuntime":
    """Load toolguards from in-memory FileTwin objects.

    Args:
        result: The toolguards code generation result containing FileTwin objects.

    Returns:
        ToolguardRuntime: A runtime instance for executing toolguards.
    """
    # Extract all FileTwin objects from the result
    file_twins: List[FileTwin] = []

    # Add domain files
    file_twins.append(result.domain.app_types)
    file_twins.append(result.domain.app_api)
    file_twins.append(result.domain.app_api_impl)

    # Add guard files from all tools
    for tool_result in result.tools.values():
        file_twins.append(tool_result.guard_file)
        # Add item guard files if they exist
        for item_guard in tool_result.item_guard_files:
            if item_guard is not None:
                file_twins.append(item_guard)

    return ToolguardRuntime(result, ctx_dir=None, file_twins=file_twins)


class ToolguardRuntime:
    """Runtime environment for executing toolguards.

    This class manages the lifecycle of toolguard execution, including:
    - Loading and caching guard functions
    - Managing Python path modifications (for directory mode)
    - Loading modules from memory (for FileTwin mode)
    - Coordinating guard function calls with proper argument injection
    """

    _original_pypath: list[str] = []

    def __init__(
        self,
        result: ToolGuardsCodeGenerationResult,
        ctx_dir: Optional[Path] = None,
        file_twins: Optional[List[FileTwin]] = None,
    ) -> None:
        """Initialize the runtime.

        Args:
            result: The toolguards code generation result.
            ctx_dir: Directory containing the toolguard files (for directory mode).
            file_twins: List of FileTwin objects (for in-memory mode).

        Note:
            Either ctx_dir or file_twins must be provided, but not both.
        """
        if ctx_dir is None and file_twins is None:
            raise ValueError("Either ctx_dir or file_twins must be provided")
        if ctx_dir is not None and file_twins is not None:
            raise ValueError("Only one of ctx_dir or file_twins should be provided")

        self._ctx_dir = ctx_dir
        self._file_twins = file_twins
        self._result = result
        self._loaded_modules: Dict[str, ModuleType] = {}

    def __enter__(self):
        self._original_pypath = list(sys.path)  # remember old path

        if self._ctx_dir is not None:
            # Directory mode: add folder to python path
            sys.path.insert(0, os.path.abspath(self._ctx_dir))
        else:
            # In-memory mode: load modules from FileTwin objects
            assert self._file_twins is not None
            self._load_modules_from_memory(self._file_twins)

        # cache the tool guards
        self._guards: Dict[str, Callable[..., Awaitable[Any]]] = {}
        for tool_name, tool_result in self._result.tools.items():
            mod_name = _file_to_module_name(tool_result.guard_file.file_name)
            module = self._get_module(mod_name)
            guard_fn = _find_function_in_module(module, tool_result.guard_fn_name)
            assert guard_fn, "Guard not found"
            self._guards[tool_name] = guard_fn

        return self

    def __exit__(self, exc_type, exc, tb):
        del self._guards

        # Clean up loaded modules if in memory mode
        if self._file_twins is not None:
            for mod_name in self._loaded_modules:
                if mod_name in sys.modules:
                    del sys.modules[mod_name]
            self._loaded_modules.clear()

        # back to original python path
        sys.path[:] = self._original_pypath
        return False

    def _load_modules_from_memory(self, file_twins: List[FileTwin]) -> None:
        """Load Python modules from FileTwin objects into sys.modules.

        Args:
            file_twins: List of FileTwin objects containing Python code.
        """
        for file_twin in file_twins:
            if not str(file_twin.file_name).endswith(".py"):
                continue

            mod_name = _file_to_module_name(file_twin.file_name)

            # Create a module spec and module
            spec = importlib.util.spec_from_loader(mod_name, loader=None)
            if spec is None:
                raise ImportError(f"Could not create spec for module {mod_name}")

            module = importlib.util.module_from_spec(spec)

            # Execute the code in the module's namespace
            exec(file_twin.content, module.__dict__)

            # Register the module
            sys.modules[mod_name] = module
            self._loaded_modules[mod_name] = module

    def _get_module(self, mod_name: str) -> ModuleType:
        """Get a module by name, either from loaded modules or by importing.

        Args:
            mod_name: The module name.

        Returns:
            The loaded module.
        """
        if self._file_twins is not None:
            # In-memory mode: get from loaded modules
            module = self._loaded_modules.get(mod_name)
            if module is None:
                raise ImportError(f"Module {mod_name} not found in loaded modules")
            return module
        else:
            # Directory mode: import normally
            return importlib.import_module(mod_name)

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
                module = self._get_module(mod_name)
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
                    # Ensure arg_val is a dict before unpacking
                    if isinstance(arg_val, dict):
                        guard_args[p_name] = param.annotation.model_construct(**arg_val)
                    else:
                        guard_args[p_name] = arg_val
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
