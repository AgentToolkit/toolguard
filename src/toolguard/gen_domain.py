

from typing import Dict, List, Optional, Tuple, Union

from toolguard.common.array import find
from toolguard.common.py import py_module
from toolguard.common.str import to_camel_case
from toolguard.common.templates import load_template
from toolguard.utils.datamodel_codegen import run as dm_codegen
from toolguard.common.open_api import OpenAPI, Operation, Parameter, ParameterIn, PathItem, Reference, RequestBody, Response, JSchema, read_openapi
from toolguard.data_types import Domain, FileTwin

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

    def generate_domain(self, oas_file:str)->Domain:
        oas = read_openapi(oas_file)
        types = FileTwin(
                file_name="domain_types.py", 
                content= dm_codegen(oas_file)
            ).save(self.cwd)

        api_cls_name = to_camel_case(oas.info.title) or "Tools_API"
        methods = self.get_oas_methods(oas)
        api = FileTwin(
                file_name="api.py", 
                content= self.generate_api(methods, api_cls_name)
            ).save(self.cwd)

        impl_cls_name = api_cls_name+"_impl"
        cls_str = self.generate_api_impl(
            methods, 
            py_module(api.file_name),
            api_cls_name,
            impl_cls_name
        )
        api_impl = FileTwin(
                file_name="api_impl.py", 
                content=cls_str
            ).save(self.cwd)
        
        return Domain(
            types= types,
            api= api,
            api_impl= api_impl
        )

    def get_oas_methods(self, oas:OpenAPI):
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
                args_str = ','.join(["self"]+[f"{arg}:{type}" for arg,type in args])
                sig = f"({args_str})->{ret}"
                methods.append({
                    "name": to_camel_case(op.operationId), 
                    "signature": sig,
                    "doc": op.description
                })
        return methods

    def generate_api(self, methods: List, cls_name: str)->str:
        template = load_template("api.j2")
        return template.render(
            class_name=cls_name,
            methods=methods
        )
    
    def generate_api_impl(self, methods: List, api_module:str, api_cls_name:str, cls_name: str)->str:
        template = load_template("api_impl.j2")
        return template.render(
            api_cls_name=api_cls_name,
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
            py_type = primitive_jschema_types_to_py(scm.type, scm.format)
            if py_type:
                return py_type
            # if scm.type == JSONSchemaTypes.array and scm.items:
            #     return f"List[{self.oas_to_py_type(scm.items, oas) or 'Any'}]"
    
if __name__ == '__main__':
    gen = OpenAPICodeGenerator("eval/airline/output")
    oas_path = "eval/airline/oas.json"
    # domain_path = "domain.py"
    domain = gen.generate_domain(oas_path)
    print("Done")