
import os
from typing import Callable, List

from toolguard.common.str import to_snake_case

def py_extension(filename:str)->str:
    return filename if filename.endswith(".py") else filename+".py" 

def un_py_extension(filename:str)->str:
    return filename[:-3] if filename.endswith(".py") else filename
    
def py_module(file_path:str):
    assert file_path
    parts = file_path.split('/')
    if parts[-1].endswith(".py"):
        parts[-1] = un_py_extension(parts[-1])
    return '.'.join([to_snake_case(part) for part in parts])

def unwrap_fn(fn: Callable)->Callable: 
    return fn.func if hasattr(fn, "func") else fn

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