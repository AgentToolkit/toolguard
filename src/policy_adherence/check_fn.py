
import ast
from typing import List

import astor
from policy_adherence.common.array import find
from policy_adherence.types import SourceFile, ToolPolicy, ToolPolicyItem
from policy_adherence.utils import py_extension, py_name

def check_fn_name(name:str)->str:
    return py_name(f"check_{name}")

def check_fn_module_name(name:str)->str:
    return py_name(check_fn_name(name))

def _create_import(src:SourceFile, *items: str):
    return ast.ImportFrom(
        module=src.file_name[:-3],# The module name (without ./)
        names=[ast.alias(name=item, asname=None) for item in items], 
        level=0 # 0 = absolute import, 1 = relative import (.)
    )

def _create_check_fn(name:str, args, body=[ast.Pass()], returns=ast.Constant(value=None))->ast.FunctionDef:
    return ast.FunctionDef(
            name=name,
            args=args,
            body=body,
            decorator_list=[],
            returns=returns
        )

def find_fn(body, fn_name:str)->ast.FunctionDef | None:
    return find(body, lambda node: isinstance(node, ast.FunctionDef) and node.name == fn_name)

def create_initial_check_fns(domain:SourceFile, common: SourceFile, tool: ToolPolicy, folder:str)->SourceFile:
    new_body = []
    new_body.append(_create_import(domain, "*"))
    # new_body.append(_create_import(common, "*"))
    
    tree = ast.parse(domain.content)
    tool_fn = find_fn(tree.body, tool.name)
    assert tool_fn
        
    args:ast.arguments = tool_fn.args
    # node.args.args.append(
    #     ast.arg(arg="chat_history", annotation=ast.Name(id="ChatHistory", ctx=ast.Load()))
    # )

    for item in tool.policy_items:
        new_body.append(_create_check_fn(check_fn_name(item.name), args, body=[ast.Pass()]))

    calls = [
        ast.Expr(
            value=ast.Call(
                func=ast.Name(id=check_fn_name(item.name), ctx=ast.Load()),
                args=[ast.Name(id="request", ctx=ast.Load())],#TODO name
                keywords=[],
            )
        )
        for item in tool.policy_items
    ]
    new_body.append(_create_check_fn(
        name=check_fn_name(tool.name),
        args=args,
        body=calls
    ))
    
    module = ast.Module(body=new_body, type_ignores=[])
    ast.fix_missing_locations(module)
    src= astor.to_source(module)
    res = SourceFile(
        file_name=py_extension(check_fn_module_name(tool.name)),
        content=src
    )
    res.save(folder)
    return res

def replace_fn_body(src:SourceFile, trg:SourceFile, fn_name:str, folder:str)->SourceFile:
    src_fn = find_fn(ast.parse(src.content).body, fn_name)
    trg_body = ast.parse(trg.content).body
    trg_fn = find_fn(trg_body, fn_name)
    assert src_fn and trg_fn

    trg_fn.body = src_fn.body
    
    module = ast.Module(body=trg_body, type_ignores=[])
    ast.fix_missing_locations(module)
    content= astor.to_source(module)
    res = SourceFile(
        file_name=py_extension(check_fn_module_name(trg.file_name)),
        content=content
    )
    res.save(folder)
    return res