import ast
import inspect
from typing import Callable, Set, cast
import sys
from pathlib import Path
from contextlib import contextmanager

from .str import to_snake_case


def py_extension(filename: str) -> str:
    return filename if filename.endswith(".py") else filename + ".py"


def un_py_extension(filename: str) -> str:
    return filename.removesuffix(".py") if filename.endswith(".py") else filename


def path_to_module(file_path: Path) -> str:
    assert file_path
    parts = list(file_path.parts)
    if parts[-1].endswith(".py"):
        parts[-1] = un_py_extension(parts[-1])
    return ".".join([to_snake_case(part) for part in parts])


def module_to_path(module: str) -> Path:
    parts = module.split(".")
    return Path(*parts[:-1], py_extension(parts[-1]))


@contextmanager
def temp_python_path(path: str | Path):
    abs_path = str(Path(path).resolve())
    if abs_path not in sys.path:
        sys.path.insert(0, abs_path)
        try:
            yield
        finally:
            sys.path.remove(abs_path)
    else:
        # Already in sys.path, no need to remove
        yield


def extract_docstr_args(func: Callable) -> str:
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
    next_sections = {
        "returns:",
        "raises:",
        "examples:",
        "notes:",
        "attributes:",
        "yields:",
    }

    # Capture lines after "Args:" that are indented
    args_lines = []
    for line in lines[args_start + 1 :]:
        # Stop if we hit a new section (like "Returns:", "Raises:", etc.)
        stripped = line.strip().lower()
        if stripped in next_sections:
            break
        args_lines.append(" " * 8 + line.strip())

    # Join all lines into a single string
    if not args_lines:
        return ""

    return "\n".join(args_lines)


def top_level_types(path: str | Path) -> Set[str]:
    nodes = ast.parse(Path(path).read_text()).body
    res = set()
    for node in nodes:
        if isinstance(node, ast.ClassDef):
            res.add(node.name)
        elif isinstance(node, ast.Assign):
            target = cast(ast.Name, node.targets[0])
            res.add(target.id)

    return res
