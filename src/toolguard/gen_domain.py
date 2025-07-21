import os
from pathlib import Path
from typing import Callable, List, Optional, Tuple, Union
from os.path import join

from toolguard.common.array import find
from toolguard.common.py import py_module, unwrap_fn
from toolguard.common.str import to_camel_case, to_snake_case
from toolguard.templates import load_template
from toolguard.py_to_oas import tools_to_openapi
from toolguard.utils.datamodel_codegen import run as dm_codegen
from toolguard.common.open_api import OpenAPI, Operation, Parameter, ParameterIn, PathItem, Reference, RequestBody, Response, JSchema, read_openapi
from toolguard.data_types import Domain, FileTwin

RUNTIME_PACKAGE_NAME="rt_toolguard"
RUNTIME_INIT_PY = "__init__.py"
RUNTIME_TYPES_PY = "data_types.py"
RUNTIME_APP_TYPES_PY = "domain_types.py"

RUNTIME_APP_API_PY = "api.py"
RUNTIME_APP_API_IMPL_PY = "api_impl.py"

class OpenAPICodeGenerator():
    cwd: str
    app_name: str

    def __init__(self, cwd:str, app_name: str) -> None:
        self.cwd = cwd
        self.app_name = app_name

    def generate_domain(self, oas_file:str, funcs: Optional[List[Callable]] = None)->Domain:
        #ToolGuard Runtime
        os.makedirs(join(self.cwd, RUNTIME_PACKAGE_NAME), exist_ok=True)
        FileTwin.load_from(
            str(Path(__file__).parent), "runtime.py")\
            .save_as(self.cwd, join(RUNTIME_PACKAGE_NAME, RUNTIME_INIT_PY))
        common = FileTwin.load_from(
            str(Path(__file__).parent), "data_types.py")\
            .save_as(self.cwd, join(RUNTIME_PACKAGE_NAME, RUNTIME_TYPES_PY))

        #APP init and Types
        oas = read_openapi(oas_file)
        os.makedirs(join(self.cwd, to_snake_case(self.app_name)), exist_ok=True)
        FileTwin(file_name=join(to_snake_case(self.app_name), "__init__.py"), content="").save(self.cwd)
        types = FileTwin(
                file_name=join(to_snake_case(self.app_name), RUNTIME_APP_TYPES_PY),
                content= dm_codegen(oas_file)
            ).save(self.cwd)

        #APP API
        api_cls_name = to_camel_case(oas.info.title) or "Tools_API"
        methods = self.get_oas_methods(oas, funcs)
        api = FileTwin(
                file_name=join(self.app_name, RUNTIME_APP_API_PY), 
                content= self.generate_api(methods, api_cls_name, py_module(types.file_name))
            ).save(self.cwd)

        #APP API Impl
        impl_cls_name = api_cls_name+"_impl"
        cls_str = self.generate_api_impl(
            methods, 
            py_module(api.file_name),
            py_module(types.file_name),
            api_cls_name,
            impl_cls_name
        )
        api_impl = FileTwin(
                file_name=join(self.app_name, RUNTIME_APP_API_IMPL_PY),
                content=cls_str
            ).save(self.cwd)
        
        return Domain(
            common = common,
            types= types,
            api_class_name=api_cls_name,
            api= api,
            api_impl_class_name=impl_cls_name,
            api_impl= api_impl
        )

    def get_oas_methods(self, oas:OpenAPI, funcs: List[Callable]|None = None):
        orign_funcs = [unwrap_fn(fn) for fn in funcs or []]

        methods = []
        for path, path_item in oas.paths.items():
            path_item = oas.resolve_ref(path_item, PathItem)
            for mtd, op in path_item.operations.items():
                op = oas.resolve_ref(op, Operation)
                if not op:
                    continue
                params = (path_item.parameters or []) + (op.parameters or [])
                params = [oas.resolve_ref(p, Parameter) for p in params]
                args, ret = self.make_signature(op, params, oas)
                args_str = ', '.join(["self"]+[f"{arg}:{type}" for arg,type in args])
                sig = f"({args_str})->{ret}"

                body = "pass"
                if orign_funcs:
                    func = find(orign_funcs or [], lambda fn: fn.__name__ == op.operationId)
                    if func:
                        args_str = ', '.join(["self"]+[f"{arg}" for arg,type in args])
                        body = f"""
        from {func.__module__} import {func.__name__}
        return {func.__name__}({args_str})
"""
                methods.append({
                    "name": to_camel_case(op.operationId), 
                    "signature": sig,
                    "doc": op.description,
                    "body": body
                })
        return methods

    def generate_api(self, methods: List, cls_name: str, types_module:str)->str:
        return load_template("api.j2").render(
            types_module=types_module,
            class_name=cls_name,
            methods=methods
        )
    
    def generate_api_impl(self, methods: List, api_module:str, types_module:str, api_cls_name:str, cls_name: str)->str:
        return load_template("api_impl.j2").render(
            api_cls_name=api_cls_name,
            types_module=types_module,
            api_module=api_module,
            class_name=cls_name,
            methods=methods
        )

    def make_signature(self, op: Operation, params: List[Parameter], oas:OpenAPI)->Tuple[Tuple[str, str], str]:
        fn_name = to_camel_case(op.operationId)
        args = []
        
        for param in params:
            if param.in_ == ParameterIn.path:
                args.append((param.name, self.oas_to_py_type(param.schema_, oas) or "Any"))

        if find(params, lambda p: p.in_ == ParameterIn.query):
            query_type = f"{fn_name}ParametersQuery"
            args.append(("args", query_type))

        req_body = oas.resolve_ref(op.requestBody, RequestBody)
        if req_body:
            scm_or_ref = req_body.content_json.schema_
            body_type = self.oas_to_py_type(scm_or_ref, oas)
            if body_type is None:
                body_type = f"{fn_name}Request"
            args.append(("args", body_type))

        rsp_or_ref = op.responses.get("200")
        rsp = oas.resolve_ref(rsp_or_ref, Response)
        if rsp:
            scm_or_ref = rsp.content_json.schema_
            if scm_or_ref:
                rsp_type = self.oas_to_py_type(scm_or_ref, oas)
                if rsp_type is None:
                    rsp_type = f"{fn_name}Response"

        return args, rsp_type
    
    def oas_to_py_type(self, scm_or_ref:Union[Reference, JSchema], oas:OpenAPI)->str | None:
        if isinstance(scm_or_ref, Reference):
            return scm_or_ref.ref.split("/")[-1]

        scm = oas.resolve_ref(scm_or_ref, JSchema)
        if scm:
            py_type = _primitive_jschema_types_to_py(scm.type, scm.format)
            if py_type:
                return py_type
            # if scm.type == JSONSchemaTypes.array and scm.items:
            #     return f"List[{self.oas_to_py_type(scm.items, oas) or 'Any'}]"
    
def _primitive_jschema_types_to_py(type:Optional[str], format:Optional[str])->Optional[str]:
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


if __name__ == '__main__':
    from pydantic import BaseModel
    class R(BaseModel):
        a:int
        b:str
        c:'R'

    from langchain.tools import tool
    @tool
    def greet(name: str, title: str = "Mr.") -> R:
        """
        Greet someone with a title.

        Args:
            name: The person's name.
            title: The person's title (default is "Mr.").
        """
        pass

    oas_path = "eval/airline/oas_1.json"
    oas = tools_to_openapi("Bla", [greet])
    oas.save(oas_path)

    # domain_path = "domain.py"
    domain = OpenAPICodeGenerator("eval/airline/output", "my_app")\
        .generate_domain(oas_path, [greet])
    print("Done")