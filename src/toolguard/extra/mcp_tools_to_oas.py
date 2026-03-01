from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

from toolguard.extra.list_mcp_tools import MCPConnectionConfig, list_mcp_tools


def mcp_tools_to_openapi(
    tools: List[Dict[str, Any]],
    title: str = "MCP Tools",
    version: str = "0.1.0",
) -> Dict[str, Any]:
    """Map a list of MCP tool descriptors to an OpenAPI 3.1 specification.

    Args:
        tools: Raw tool descriptor dicts, as returned by :func:`list_mcp_tools`.
        title: Value for ``info.title`` in the generated spec.
        version: Value for ``info.version`` in the generated spec.

    Returns:
        An OpenAPI 3.1 document as a plain Python dict.
    """
    paths: dict[str, Any] = {}
    all_schemas = []

    for tool in tools:
        tool_name = _pick_mcp_tool_name(tool)
        tool_desc = _pick_tool_description(tool)
        summary = _pick_tool_summary(tool)

        input_schema = _normalize_schema(_pick_input_schema(tool))
        output_schema = _normalize_schema(_pick_output_schema(tool))
        all_schemas.extend([input_schema, output_schema])

        route = f"/{tool_name}"
        paths[route] = {
            "post": {
                "operationId": tool_name,
                "summary": summary or tool_name,
                "description": (tool_desc or "").strip(),
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": input_schema}},
                },
                "responses": {
                    "200": {
                        "description": _pick_output_description(tool),
                        "content": {"application/json": {"schema": output_schema}},
                    }
                },
            }
        }

    components_schemas = _lift_defs_to_components(all_schemas)

    return {
        "openapi": "3.1.0",
        "info": {
            "title": title,
            "version": version,
            "description": (
                "OpenAPI export of MCP tools metadata. "
                "Contains only operation descriptions and input/output schemas to support code generation."
            ),
        },
        "paths": paths,
        "components": {"schemas": components_schemas},
    }


# ============================================================
# Metadata pickers
# ============================================================


def _pick_mcp_tool_name(tool: dict[str, Any]) -> str:
    return tool.get("name") or "unknown-tool"


def _pick_tool_description(tool: dict[str, Any]) -> str:
    return tool.get("description") or tool.get("summary") or ""


def _pick_output_description(tool: dict[str, Any]) -> str:
    return (
        tool.get("outputDescription") or tool.get("resultDescription") or "Tool result"
    )


def _pick_input_schema(tool: dict[str, Any]) -> dict[str, Any]:
    for key in ("inputSchema", "input_schema", "parameters", "schema"):
        schema = tool.get(key)
        if isinstance(schema, dict) and schema:
            return dict(schema)
    return {"type": "object", "additionalProperties": True}


def _pick_output_schema(tool: dict[str, Any]) -> dict[str, Any]:
    for key in (
        "outputSchema",
        "output_schema",
        "responseSchema",
        "response_schema",
        "returnSchema",
        "return_schema",
        "resultSchema",
        "result_schema",
    ):
        schema = tool.get(key)
        if isinstance(schema, dict) and schema:
            return dict(schema)
    return {}


def _pick_tool_summary(tool: dict[str, Any]) -> str:
    text = (tool.get("description") or tool.get("summary") or "").strip()
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    m = re.search(r"[.!?]\s", text)
    if not m:
        return text
    return text[: m.end() - 1].strip()


# ============================================================
# Schema normalization
# ============================================================


def _normalize_schema(schema: dict[str, Any]) -> dict[str, Any]:
    s = dict(schema or {})
    s.pop("$schema", None)
    if "type" not in s and isinstance(s.get("properties"), dict):
        s["type"] = "object"
    return s


# ============================================================
# $defs lifting
# ============================================================


def _lift_defs_to_components(schemas: List[Dict]) -> dict[str, Any]:
    """Lift top-level ``$defs`` from each schema into ``components.schemas``
    and rewrite all ``$ref: "#/$defs/<Name>"`` to ``"#/components/schemas/<Name>"``.
    """

    def _rewrite_refs(node: Any) -> Any:
        if isinstance(node, list):
            return [_rewrite_refs(item) for item in node]
        if not isinstance(node, dict):
            return node
        result = {}
        for k, v in node.items():
            if k == "$ref" and isinstance(v, str) and v.startswith("#/$defs/"):
                def_name = v[len("#/$defs/") :]
                result[k] = f"#/components/schemas/{def_name}"
            else:
                result[k] = _rewrite_refs(v)
        return result

    out: dict[str, Any] = {}
    for schema in schemas:
        if not isinstance(schema, dict):
            continue
        defs = schema.get("$defs")
        if not isinstance(defs, dict) or not defs:
            continue
        out.update(defs)
        schema.pop("$defs", None)
        for k in list(schema.keys()):
            schema[k] = _rewrite_refs(schema[k])

    return out


def main() -> None:
    cfg = MCPConnectionConfig(
        mcp_url="http://localhost:8765/mcp",
        # gateway_tools_url="http://127.0.0.1:4444/tools",
        # bearer_token=os.environ.get("TOKEN", ""),
    )
    out_path = "./out/gateway_mcp_tools_openapi_direct.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tools = list_mcp_tools(cfg)
    oas = mcp_tools_to_openapi(tools, title="My MCP Tools", version="1.0.0")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(oas, f, indent=2)
    print(f"Wrote OpenAPI JSON to: {out_path}")


if __name__ == "__main__":
    main()

# Made with Bob
