
import ast
import os
import astor

from policy_adherence.common.str import to_snake_case
from policy_adherence.types import SourceFile

def py_extension(filename:str)->str:
    return filename if filename.endswith(".py") else filename+".py" 

def un_py_extension(filename:str)->str:
    return filename[:-3] if filename.endswith(".py") else filename
    
def create_import(module_name:str, *items: str):
    return ast.ImportFrom(
        module=module_name,
        names=[ast.alias(name=item, asname=None) for item in items], 
        level=0 # 0 = absolute import, 1 = relative import (.)
    )

def create_fn(name:str, args, body=[ast.Pass()], returns=ast.Constant(value=None))->ast.FunctionDef:
    return ast.FunctionDef(
            name=name,
            args=args,
            body=body,
            decorator_list=[],
            returns=returns
        ) # type: ignore

def call_fn(fn_name:str, *args:str)->ast.Expr:
    return ast.Expr(
        value=ast.Call(
            func=ast.Name(id=fn_name, ctx=ast.Load()),
            args=[ast.Name(id=arg, ctx=ast.Load()) for arg in args],
            keywords=[],
        )
    )

def py_module(file_path:str):
    assert file_path
    parts = file_path.split('/')
    if parts[-1].endswith(".py"):
        parts[-1] = un_py_extension(parts[-1])
    return '.'.join([to_snake_case(part) for part in parts])

def save_py_body(body, file_name:str, py_path:str)->SourceFile:
    module = ast.Module(body=body, type_ignores=[])
    ast.fix_missing_locations(module)
    src= astor.to_source(module)
    res = SourceFile(
        file_name=file_name,
        content=src
    )
    res.save(py_path)
    return res

def create_init_py(folder):
    with open(os.path.join(folder, "__init__.py"), "w") as file:
        pass