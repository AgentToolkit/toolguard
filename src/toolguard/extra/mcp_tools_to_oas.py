from __future__ import annotations

import json
import os
from typing import Any, Dict, List
from mcp.types import Tool
from fastmcp.client import Client


async def list_mcp_tools(client: Client) -> list[Tool]:
    async with client:
        return await client.list_tools()


def mcp_tools_to_openapi(
    tools: List[Tool],
    title: str = "MCP Tools",
    version: str = "0.1.0",
) -> Dict[str, Any]:
    """Map a list of MCP tool descriptors to an OpenAPI 3.1 specification.

    Args:
        tools: List of MCP Tool objects, as returned by :func:`list_mcp_tools`.
        title: Value for ``info.title`` in the generated spec.
        version: Value for ``info.version`` in the generated spec.

    Returns:
        An OpenAPI 3.1 document as a plain Python dict.
    """
    paths: dict[str, Any] = {}
    all_schemas = []

    for tool in tools:
        # Extract first sentence from description for summary
        summary = (
            tool.description.split(". ")[0]
            if tool.description and ". " in tool.description
            else tool.description
        )

        input_schema = _normalize_schema(tool.inputSchema)
        output_schema = _normalize_schema(tool.outputSchema or {})
        all_schemas.extend([input_schema, output_schema])

        route = f"/{tool.name}"
        paths[route] = {
            "post": {
                "operationId": tool.name,
                "summary": summary or tool.name,
                "description": tool.description,
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": input_schema}},
                },
                "responses": {
                    "200": {
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


async def main() -> None:
    from fastmcp.client import StreamableHttpTransport

    transport = StreamableHttpTransport(url="http://127.0.0.1:8765/mcp")
    mcp_client = Client(transport)
    tools = await list_mcp_tools(mcp_client)
    oas = mcp_tools_to_openapi(tools, title="My MCP Tools", version="1.0.0")

    out_path = "./output/mcp_tools_openapi_direct.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(oas, f, indent=2)
    print(f"Wrote OpenAPI JSON to: {out_path}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

# Made with Bob
