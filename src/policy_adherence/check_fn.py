
import ast
from typing import List, Tuple

import astor
from policy_adherence.common.array import find
from policy_adherence.types import SourceFile, ToolPolicy, ToolPolicyItem
from policy_adherence.utils import py_extension, py_name, un_py_extension

def check_fn_name(name:str)->str:
    return py_name(f"check_{name}")

def check_fn_module_name(name:str)->str:
    return py_name(check_fn_name(name))

class CheckFnManager():

    cwd: str
    def __init__(self, cwd:str) -> None:
        self.cwd = cwd

    def create_initial_check_fns(self, domain:SourceFile, common: SourceFile, tool: ToolPolicy, folder:str)->Tuple[SourceFile, List[SourceFile]]:
        tree = ast.parse(domain.content)
        tool_fn = self._find_fn(tree.body, tool.name)
        assert tool_fn
        fn_args:ast.arguments = tool_fn.args
        # node.args.args.append(
        #     ast.arg(arg="chat_history", annotation=ast.Name(id="ChatHistory", ctx=ast.Load()))
        # )
        
        item_files = [self._create_item_module(item, domain, common, fn_args) 
                for item in tool.policy_items]
        
        new_body = []
        #imports
        new_body.append(
            self._create_import(
                un_py_extension(domain.file_name), 
                "*"
        ))
        # new_body.append(_create_import(common, "*"))
        for item_module, item in zip(item_files, tool.policy_items):
            import_module = un_py_extension(item_module.file_name)
            import_item = check_fn_name(item.name)
            new_body.append(self._create_import(import_module, import_item))
        
        call_item_fns = [
            ast.Expr(
                value=ast.Call(
                    func=ast.Name(id=check_fn_name(item.name), ctx=ast.Load()),
                    args=[ast.Name(id="request", ctx=ast.Load())],#TODO name
                    keywords=[],
                )
            )
            for item in tool.policy_items
        ]
        new_body.append(self._create_check_fn(
            name=check_fn_name(tool.name),
            args=fn_args,
            body=call_item_fns
        ))
        file_name = py_extension(check_fn_module_name(tool.name))
        tool_file = self.py_to_file(new_body, file_name)
        return (tool_file, item_files)
     
    def py_to_file(self, body, file_name:str):
        module = ast.Module(body=body, type_ignores=[])
        ast.fix_missing_locations(module)
        src= astor.to_source(module)
        res = SourceFile(
            file_name=file_name,
            content=src
        )
        res.save(self.cwd)
        return res

    def _find_fn(self, body, fn_name:str)->ast.FunctionDef | None:
        return find(body, lambda node: isinstance(node, ast.FunctionDef) and node.name == fn_name)

    def _create_item_module(self, tool_item: ToolPolicyItem, domain:SourceFile, common: SourceFile, fn_args:ast.arguments)->SourceFile:
        body = []
        body.append(
            self._create_import(
                un_py_extension(domain.file_name), 
                "*"
        ))

        body.append(self._create_check_fn(
            name=check_fn_name(tool_item.name),
            args=fn_args
        ))

        file_name = py_extension(check_fn_module_name(tool_item.name))
        return self.py_to_file(body, file_name)

    
    def _create_import(self, module_name:str, *items: str):
        return ast.ImportFrom(
            module=module_name,
            names=[ast.alias(name=item, asname=None) for item in items], 
            level=0 # 0 = absolute import, 1 = relative import (.)
        )

    def _create_check_fn(self, name:str, args, body=[ast.Pass()], returns=ast.Constant(value=None))->ast.FunctionDef:
        return ast.FunctionDef(
                name=name,
                args=args,
                body=body,
                decorator_list=[],
                returns=returns
            )
