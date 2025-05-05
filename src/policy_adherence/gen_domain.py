

import ast
import os
from typing import List, Optional, Union

import astor
from policy_adherence.common.array import find
from policy_adherence.common.py import create_class
from policy_adherence.common.str import to_camel_case, to_snake_case
from policy_adherence.tools.datamodel_codegen import run as dm_codegen
from policy_adherence.common.open_api import OpenAPI, Operation, Parameter, ParameterIn, PathItem, Reference, RequestBody, Response, JSchema, read_openapi
from policy_adherence.types import SourceFile

def primitive_jschema_types_to_py(type:Optional[str], format:Optional[str])->Optional[str]:
    #https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.2.md#data-types
    if type == "string":
        if format == "date":
            return "datetime.date"
        if format == "date-time":
            return "datetime.datetime"
        if format in ["byte", "binary"]:
            return "bytes"
        return "str"
    if type == "integer":
        return "int"
    if type == "number":
        return "float"
    if type == "boolean":
        return "bool"
    return None

class OpenAPICodeGenerator():
    cwd: str
    def __init__(self, cwd:str) -> None:
        self.cwd = cwd

    def generate_domain(self, oas_file:str, domain_py_file:str)->SourceFile:
        #types
        types_src = dm_codegen(oas_file)

        #apis
        api_src = self.generate_api(oas_file, types_src)

        content = f"{types_src}\n\n# Tool interfaces\n{api_src}\n"
        src = SourceFile(file_name=domain_py_file, content=content)
        src.save(self.cwd)
        return src

    def generate_api(self, oas_file:str, types_src: str)->str:
        oas = read_openapi(oas_file)
        
        new_body = []
        new_body.append(self.import_typing())

        cls_name = to_camel_case(oas.info.title) or "Tools_API"
        api_cls = create_class(
            name=cls_name,
            base_class_names=["Protocol"]
        )
        new_body.append(api_cls)

        for path, path_item in oas.paths.items():
            path_item = oas.resolve_ref(path_item, PathItem)
            for mtd, op in path_item.operations.items():
                op = oas.resolve_ref(op, Operation)
                params = (path_item.parameters or []) + (op.parameters or [])
                params = [oas.resolve_ref(p, Parameter) for p in params]
                mtd = self.make_method(op, params, oas)
                api_cls.body.append(mtd)
        
        module = ast.Module(body=new_body, type_ignores=[])
        ast.fix_missing_locations(module)
        return astor.to_source(module)

    def make_method(self, op: Operation, params: List[Parameter], oas:OpenAPI)->ast.FunctionDef:
        fn_name = op.operationId

        args = [ast.arg(arg="self")]
        for param in params:
            if param.in_ == ParameterIn.path:
                args.append(self.make_arg(param, oas))

        if find(params, lambda p: p.in_ == ParameterIn.query):
            query_type = f"{to_camel_case(fn_name)}ParametersQuery"
            args.append(ast.arg(
                arg="query", 
                annotation=ast.Name(id=query_type, ctx=ast.Load())
            ))

        req_body = oas.resolve_ref(op.requestBody, RequestBody)
        if req_body:
            scm_or_ref = req_body.content_json.schema_
            body_type = self.map_oas_to_py_type(scm_or_ref, oas)
            if body_type is None:
                body_type = f"{to_camel_case(fn_name)}Request"
            args.append(ast.arg(
                arg="request", 
                annotation=ast.Name(id=body_type, ctx=ast.Load())
            ))

        return_type = None
        rsp_or_ref = op.responses.get("200")
        rsp = oas.resolve_ref(rsp_or_ref, Response)
        if rsp:
            scm_or_ref = rsp.content_json.schema_
            if scm_or_ref:
                rsp_type = self.map_oas_to_py_type(scm_or_ref, oas)
                if rsp_type is None:
                    rsp_type = f"{to_camel_case(fn_name)}Response"
                return_type = ast.Name(id=rsp_type, ctx=ast.Load())

        mtd = ast.FunctionDef(
            name=to_snake_case(fn_name),
            args=ast.arguments(
                args=args,  # Normal arguments
                posonlyargs=[],  # No positional-only arguments
                vararg=None,  # No *args
                kwonlyargs=[],  # No keyword-only arguments
                kw_defaults=[],  # No keyword defaults
                defaults=[]  # No default values
            ),
            body=[ast.Pass()],  # Empty function body (for now)
            decorator_list=[],  # No decorators
            returns=return_type  # Return type annotation
        ) # type: ignore
        
        doc = ast.Expr(value=ast.Constant(op.description))
        mtd.body.insert(0, doc)
        return mtd
    
    def map_oas_to_py_type(self, scm_or_ref:Union[Reference, JSchema], oas:OpenAPI)->str | None:
        if isinstance(scm_or_ref, Reference):
            return scm_or_ref.ref.split("/")[-1]

        scm = oas.resolve_ref(scm_or_ref, JSchema)
        py_type = primitive_jschema_types_to_py(scm.type, scm.format)
        if py_type:
            return py_type
        if scm.type == "array":
            return f"List[{self.map_oas_to_py_type(scm.items, oas) or 'Any'}]"
    
    def make_arg(self, param: Parameter, oas:OpenAPI):
        py_type = self.map_oas_to_py_type(param.schema_, oas) or "Any"
        return ast.arg(
            arg=param.name, 
            annotation=ast.Name(id=py_type, ctx=ast.Load()))

    def import_typing(self):
        return ast.ImportFrom(
            module="typing",
            names=[
                ast.alias(name="Any", asname=None),
                ast.alias(name="Dict", asname=None),
                ast.alias(name="List", asname=None),
                ast.alias(name="Protocol", asname=None),
            ], 
            level=0 
        )
    

if __name__ == '__main__':
    gen = OpenAPICodeGenerator("tau_airline/output")
    oas_path = "tau_airline/input/openapi.yaml"
    domain_path = "domain.py"
    domain = gen.generate_domain(oas_path, domain_path)
    print("Done")