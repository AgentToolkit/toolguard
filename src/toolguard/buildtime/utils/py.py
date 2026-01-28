import ast
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Set, cast

from toolguard.buildtime.utils.str import to_camel_case, to_snake_case


def py_extension(filename: str) -> str:
    return filename if filename.endswith(".py") else filename + ".py"


def un_py_extension(filename: str) -> str:
    return filename.removesuffix(".py") if filename.endswith(".py") else filename


def path_to_module(file_path: Path) -> str:
    assert file_path
    parts = list(file_path.parts)
    if parts[-1].endswith(".py"):
        parts[-1] = un_py_extension(parts[-1])
    return ".".join([to_py_func_name(part) for part in parts])


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


def to_py_class_name(txt: str) -> str:
    return to_camel_case(txt)


def to_py_func_name(txt: str) -> str:
    return to_snake_case(txt)


def to_py_module_name(txt: str) -> str:
    return to_py_func_name(txt)


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
