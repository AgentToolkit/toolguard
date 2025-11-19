
import importlib
import os
import inspect
from types import ModuleType
from typing import Callable
import importlib.util
from toolguard.common.str import to_snake_case

def py_extension(filename:str)->str:
    return filename if filename.endswith(".py") else filename+".py" 

def un_py_extension(filename:str)->str:
    return filename.removesuffix(".py") if filename.endswith(".py") else filename
    
def path_to_module(file_path:str)->str:
    assert file_path
    parts = file_path.split('/')
    if parts[-1].endswith(".py"):
        parts[-1] = un_py_extension(parts[-1])
    return '.'.join([to_snake_case(part) for part in parts])

def module_to_path(module:str)->str:
    parts = module.split(".")
    return os.path.join(*parts[:-1], py_extension(parts[-1]))

def unwrap_fn(fn: Callable)->Callable: 
    return fn.func if hasattr(fn, "func") else fn

def load_module_from_path(file_path: str, py_root:str) -> ModuleType:
    full_path = os.path.abspath(os.path.join(py_root, file_path))
    if not os.path.exists(full_path):
        raise ImportError(f"Module file does not exist: {full_path}")

    module_name = path_to_module(file_path)

    spec = importlib.util.spec_from_file_location(module_name, full_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module spec from {full_path}")

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)  # type: ignore
    except Exception as e:
        raise ImportError(f"Failed to execute module '{module_name}': {e}")

    return module

import sys
from pathlib import Path
from contextlib import contextmanager
@contextmanager
def temp_python_path(path: str):
    path = str(Path(path).resolve())
    if path not in sys.path:
        sys.path.insert(0, path)
        try:
            yield
        finally:
            sys.path.remove(path)
    else:
        # Already in sys.path, no need to remove
        yield

def extract_docstr_args(func:Callable) -> str:
    doc = inspect.getdoc(func)
    if not doc:
        return ""

    lines = doc.splitlines()
    args_start = None
    for i, line in enumerate(lines):
        if line.strip().lower() == "args:":
            args_start = i
            break

    if args_start is None:
        return ""


    # List of known docstring section headers
    next_sections = {"returns:", "raises:", "examples:", "notes:", "attributes:", "yields:"}

    # Capture lines after "Args:" that are indented
    args_lines = []
    for line in lines[args_start + 1:]:
        # Stop if we hit a new section (like "Returns:", "Raises:", etc.)
        stripped = line.strip().lower()
        if stripped in next_sections:
            break
        args_lines.append(" "*8 + line.strip())

    # Join all lines into a single string
    if not args_lines:
        return ""

    return "\n".join(args_lines)

def get_func_signature(obj)->str:
	if inspect.isfunction(obj):
		return inspect.signature(obj)
	if hasattr(obj, "func") and inspect.isfunction(obj.func): # a @tool
		return inspect.signature(obj.func)
	if hasattr(obj, "args_schema"):
		schema = obj.args_schema
		fields = schema.model_fields
		params = ", ".join(
			f"{name}: {field.annotation.__name__ if hasattr(field.annotation, '__name__') else field.annotation}"
			for name, field in fields.items()
		)
		return f"({params})"
	return None