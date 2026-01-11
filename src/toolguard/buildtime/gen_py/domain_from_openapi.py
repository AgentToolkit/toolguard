import os
from pathlib import Path
from typing import List, Optional, Set, Tuple
from os.path import join

from toolguard.runtime.data_types import FileTwin, RuntimeDomain, ARGS_PARAM
from toolguard.buildtime.utils.array import find
from toolguard.buildtime.utils.py import top_level_types, module_to_path
from toolguard.buildtime.utils.str import to_camel_case, to_pascal_case, to_snake_case
from toolguard.buildtime.gen_py.templates import load_template
from toolguard.buildtime.utils.datamodel_codegen import run as dm_codegen
from toolguard.buildtime.utils.open_api import (
    OpenAPI,
    Operation,
    Parameter,
    ParameterIn,
    PathItem,
    Reference,
    RequestBody,
    Response,
    JSchema,
    read_openapi,
)


def generate_domain_from_openapi(
    py_path: Path, app_name: str, openapi_file: Path
) -> RuntimeDomain:
    # APP Types
    oas = read_openapi(openapi_file)
    os.makedirs(join(py_path, to_snake_case(app_name)), exist_ok=True)

    types_name = f"{app_name}_types"
    types_module_name = f"{app_name}.{types_name}"
    types = FileTwin(
        file_name=module_to_path(types_module_name), content=dm_codegen(openapi_file)
    ).save(py_path)
    type_names = top_level_types(py_path / types.file_name)

    # APP Init
    FileTwin(
        file_name=Path(to_snake_case(app_name)) / "__init__.py",
        content=f"from . import {types_name}",
    ).save(py_path)

    # APP API
    api_cls_name = to_camel_case("I " + app_name)
    methods = _get_oas_methods(oas, type_names)
    api_module_name = to_snake_case(f"{app_name}.i_{app_name}")
    api = FileTwin(
        file_name=module_to_path(api_module_name),
        content=_generate_api(methods, api_cls_name, types_module_name),
    ).save(py_path)

    # APP API Impl
    impl_cls_name = to_camel_case(app_name + " impl")
    impl_module_name = to_snake_case(f"{app_name}.{app_name}_impl")
    cls_str = _generate_api_impl(
        methods, api_module_name, types_module_name, api_cls_name, impl_cls_name
    )
    api_impl = FileTwin(
        file_name=module_to_path(impl_module_name), content=cls_str
    ).save(py_path)

    return RuntimeDomain(
        app_name=app_name,
        app_types=types,
        app_api_class_name=api_cls_name,
        app_api=api,
        app_api_impl_class_name=impl_cls_name,
        app_api_impl=api_impl,
        app_api_size=len(methods),
    )


def _get_oas_methods(oas: OpenAPI, type_names: Set[str]):
    methods = []
    for path, p_item in oas.paths.items():  # noqa: B007
        path_item = oas.resolve_ref(p_item, PathItem)
        assert path_item
        for mtd, op in path_item.operations.items():  # noqa: B007
            op = oas.resolve_ref(op, Operation)
            if not op:
                continue
            params = (path_item.parameters or []) + (op.parameters or [])
            params = [oas.resolve_ref(p, Parameter) for p in params]
            args, ret = _make_signature(op, params, oas, type_names)  # type: ignore
            args_str = ", ".join(["self"] + [f"{arg}:{typ}" for arg, typ in args])
            sig = f"({args_str})->{ret}"

            fn_name = to_snake_case(op.operationId or "func")
            body = f"return self._delegate.invoke('{fn_name}', {ARGS_PARAM}.model_dump(), {ret})"
            # if orign_funcs:
            #     func = find(orign_funcs or [], lambda fn: fn.__name__ == op.operationId) # type: ignore
            #     if func:
            #         body = _call_fn_body(func)
            methods.append(
                {
                    "name": to_snake_case(op.operationId),  # type: ignore
                    "signature": sig,
                    "doc": op.description,
                    "body": body,
                }
            )
    return methods


def _generate_api(methods: List, cls_name: str, types_module: str) -> str:
    return load_template("api.j2").render(
        types_module=types_module, class_name=cls_name, methods=methods
    )


def _generate_api_impl(
    methods: List, api_module: str, types_module: str, api_cls_name: str, cls_name: str
) -> str:
    return load_template("api_impl.j2").render(
        api_cls_name=api_cls_name,
        types_module=types_module,
        api_module=api_module,
        class_name=cls_name,
        methods=methods,
    )


ANY = "Any"


def _make_signature(
    op: Operation, params: List[Parameter], oas: OpenAPI, type_names: Set[str]
) -> Tuple[List[Tuple[str, str]], str]:
    fn_name = to_camel_case(op.operationId or "operationId")

    args = []
    for param in params:
        if param.in_ == ParameterIn.path and param.schema_:
            param_type = _oas_to_py_type(param.schema_, oas, type_names) or ANY
            args.append((param.name, param_type))

    if find(params, lambda p: p.in_ == ParameterIn.query):
        param_type = (
            _oas_to_py_type(param.schema_, oas, type_names, f"{fn_name}ParametersQuery")
            or ANY
        )
        args.append((ARGS_PARAM, param_type))

    req_body = oas.resolve_ref(op.requestBody, RequestBody)
    if req_body and req_body.content_json:
        scm_or_ref = req_body.content_json.schema_
        if scm_or_ref:
            body_type = (
                _oas_to_py_type(scm_or_ref, oas, type_names, f"{fn_name}Request") or ANY
            )
            args.append((ARGS_PARAM, body_type))

    if op.responses:
        rsp_or_ref = op.responses.get("200")
        rsp = oas.resolve_ref(rsp_or_ref, Response)
        if rsp:
            scm_or_ref = rsp.content_json.schema_
            if scm_or_ref:
                # try first to get the primitive type response. then, a Response model (generated for 400 error codes)
                rsp_type = (
                    _oas_to_py_type(scm_or_ref, oas, set())
                    or _oas_to_py_type(
                        scm_or_ref, oas, type_names, f"{fn_name}Response"
                    )
                    or ANY
                )

    return args, rsp_type


def _oas_to_py_type(
    scm_or_ref: Reference | JSchema | None,
    oas: OpenAPI,
    type_names: Set[str],
    proposed_type_name: str | None = None,
) -> Optional[str]:
    if proposed_type_name and proposed_type_name in type_names:
        return proposed_type_name

    if isinstance(scm_or_ref, Reference):
        typ = scm_or_ref.ref.split("/")[-1]
        typ = to_pascal_case(typ)
        if typ in type_names:
            return typ

    scm = oas.resolve_ref(scm_or_ref, JSchema)
    if scm:
        if scm.type:
            py_type = _primitive_jschema_types_to_py(scm.type, scm.format)
            if py_type:
                return py_type
        # if scm.type == JSONSchemaTypes.array and scm.items:
        #     return f"List[{oas_to_py_type(scm.items, oas) or 'Any'}]"

    return None


def _primitive_jschema_types_to_py(
    type: Optional[str], format: Optional[str]
) -> Optional[str]:
    # https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.2.md#data-types
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
