from typing import Any, Dict, List

from toolguard.buildtime.gen_spec.data_types import ToolInfo, ToolInfoParam
from toolguard.buildtime.utils.jschema import JSchema
from toolguard.buildtime.utils.open_api import (
    OpenAPI,
    Operation,
    PathItem,
    RequestBody,
    Response,
)


def openapi_to_toolinfos(oas: OpenAPI) -> List[ToolInfo]:
    def _operation_to_tool_info(
        path: str, method: str, operation: Operation
    ) -> ToolInfo:
        operation_id = (
            operation.operationId or f"{method}_{path.strip('/').replace('/', '_')}"
        )
        func_name = operation_id
        summary = operation.summary or ""
        description = operation.description or summary
        request_body: RequestBody | None = oas.resolve_ref(
            operation.requestBody, RequestBody
        )
        params = _parse_request_body(request_body) if request_body else {}
        resps = {
            code: oas.resolve_ref(resp, Response)
            for code, resp in operation.responses.items()
        }
        signature = _generate_signature(func_name, params, resps)

        return ToolInfo(
            name=func_name,
            summary=summary,
            description=description,
            parameters=params,
            signature=signature,
        )

    def _parse_request_body(request_body: RequestBody) -> Dict[str, ToolInfoParam]:
        content = request_body.content_json
        if not content or not content.schema_:
            return {}

        schema = oas.resolve_ref(content.schema_, JSchema)
        assert schema
        props = schema.properties or {}
        props = {prop: oas.resolve_ref(scm, JSchema) for prop, scm in props.items()}
        required = schema.required or []

        params = {}
        for param_name, param_schema in props.items():
            resolved_schema = oas.resolve_ref(param_schema, JSchema)
            param_type = _resolve_schema_type(resolved_schema)
            param_desc = resolved_schema.description
            params[param_name] = ToolInfoParam(
                type=param_type, description=param_desc, required=param_name in required
            )
        return params

    def _resolve_schema_type(schema: JSchema | None) -> str:
        if not schema:
            return "Any"

        if schema.anyOf:
            return (
                "Union["
                + ", ".join(
                    _resolve_schema_type(oas.resolve_ref(s, JSchema))
                    for s in schema.anyOf
                )
                + "]"
            )
        if schema.oneOf:
            return (
                "Union["
                + ", ".join(
                    _resolve_schema_type(oas.resolve_ref(s, JSchema))
                    for s in schema.oneOf
                )
                + "]"
            )

        if schema.type == "array":
            item_type = _resolve_schema_type(oas.resolve_ref(schema.items, JSchema))
            return f"List[{item_type}]"

        if schema.type == "object":
            return "Dict[str, Any]"

        return {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
            "object": "Dict[str, Any]",
        }.get(str(schema.type), "Any")

    def _generate_signature(
        class_name: str, params: Dict[str, Any], responses: Dict[str, Response]
    ) -> str:
        args = ", ".join(f"{name}: {meta.type}" for name, meta in params.items())
        out = "str"
        if responses and "200" in responses:
            resp = responses["200"]
            app_json = resp.content_json
            out = "Any"
            if app_json:
                schema = oas.resolve_ref(app_json.schema_, JSchema)
                out = _resolve_schema_type(schema)
        return f"{class_name}({args}) -> {out}"

    operations = []
    for path, p_item in oas.paths.items():
        path_item = oas.resolve_ref(p_item, PathItem)
        assert path_item
        for mtd, op in path_item.operations.items():
            op = oas.resolve_ref(op, Operation)
            if not op:
                continue
            tool_info = _operation_to_tool_info(path, mtd, op)
            operations.append(tool_info)
    return operations
