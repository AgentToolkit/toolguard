from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

import httpx


def export_mcp_tools_as_openapi(cfg: ExportConfig) -> Dict[str, Any]:
    """
    Returns an OpenAPI 3.1 spec where each MCP tool becomes:
      POST /tools/{tool_name}

    Notes:
    - Input schema: from tool metadata (inputSchema/parameters/...)
    - Output schema: only if tool metadata provides it; otherwise exported as "any" ({})
    """
    tools_url = f"{cfg.gateway_url.rstrip('/')}/tools"
    mcp_endpoint = f"{cfg.gateway_url.rstrip('/')}/servers/{cfg.server_uuid}/mcp/"

    with httpx.Client(
        headers=_auth_headers(cfg.bearer_token), timeout=30.0, follow_redirects=True
    ) as client:
        r = client.get(tools_url)
        r.raise_for_status()
        tools: list[dict[str, Any]] = r.json()
        if not isinstance(tools, list):
            raise TypeError(f"Expected list from {tools_url}, got {type(tools)}")

    paths: dict[str, Any] = {}

    for tool in tools:
        tool_name = _pick_mcp_tool_name(tool)  # e.g. "math-upstream-add-tool"
        tool_id = _pick_tool_id(tool)
        desc = _pick_tool_description(tool)
        input_schema = _pick_input_schema(tool)

        # NEW: output schema (if present); else "any"
        output_schema, output_schema_found = _pick_output_schema(tool)

        tool_display_name = _pick_tool_display_name(tool)
        tool_original_name = _pick_mcp_tool_original_name(tool)

        route = f"/tools/{tool_name}"

        paths[route] = {
            "post": {
                "operationId": f"{tool_original_name}",
                "tool_name": f"{tool_name}",
                "custom_name": f"{tool_display_name}",
                "summary": f"Call MCP tool: {tool_display_name}",
                "description": (f"{desc}" or "").strip(),
                "tags": ["mcp-tools"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": input_schema,
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Tool execution result (schema depends on tool/runtime).",
                        "content": {
                            "application/json": {
                                # CHANGED: no longer hard-coded
                                "schema": output_schema,
                            }
                        },
                    }
                },
                # Vendor extensions so another system knows how to really execute
                "x-mcp-server-uuid": cfg.server_uuid,
                "x-mcp-endpoint": mcp_endpoint,
                "x-mcp-tool-id": tool_id,
                "x-mcp-upstream-meta": tool,  # embed raw tool metadata
                "x-mcp-output-schema-found": output_schema_found,
            }
        }

    spec: dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {
            "title": cfg.title,
            "version": cfg.version,
            "description": (
                "Export of MCP Gateway tools as an OpenAPI contract. "
                "These paths represent tool invocations; execution should be routed via MCP using x-mcp-* fields.\n"
                "Input schemas are sourced from tool metadata. Output schemas are included only when the tool metadata provides them; otherwise exported as 'any'."
            ),
        },
        "servers": [{"url": cfg.gateway_url.rstrip("/")}],
        "paths": paths,
        "tags": [{"name": "mcp-tools"}],
        "components": {
            "securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}}
        },
        "security": [{"bearerAuth": []}],
        "x-generated-at": datetime.now(timezone.utc).isoformat(),
        "x-mcp": {
            "gateway_url": cfg.gateway_url.rstrip("/"),
            "virtual_server_uuid": cfg.server_uuid,
            "mcp_endpoint": mcp_endpoint,
            "source_tools_endpoint": tools_url,
        },
    }

    return spec


@dataclass(frozen=True)
class ExportConfig:
    gateway_url: str
    bearer_token: str
    server_uuid: str
    title: str = "MCP Gateway Tools"
    version: str = "0.1.0"


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _pick_mcp_tool_original_name(tool: dict[str, Any]) -> str:
    return tool.get("originalName") or "unknown-tool"


def _pick_mcp_tool_name(tool: dict[str, Any]) -> str:
    return tool.get("name") or "unknown-tool"


def _pick_tool_id(tool: dict[str, Any]) -> str:
    return tool.get("id") or "unknown-tool"


def _pick_tool_display_name(tool: dict[str, Any]) -> str:
    return (
        tool.get("displayName")
        or tool.get("customName")
        or tool.get("name")
        or "unknown-tool"
    )


def _pick_tool_description(tool: dict[str, Any]) -> str:
    return tool.get("description") or tool.get("summary") or ""


def _pick_input_schema(tool: dict[str, Any]) -> dict[str, Any]:
    for key in ("inputSchema", "input_schema", "parameters", "schema"):
        schema = tool.get(key)
        if isinstance(schema, dict) and schema:
            schema = dict(schema)
            schema.pop("$schema", None)
            if "type" not in schema and "properties" in schema:
                schema["type"] = "object"
            return schema

    return {"type": "object", "additionalProperties": True}


def _pick_output_schema(tool: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """
    Output schema is NOT standardized by MCP/Gateways.
    If present in metadata, use it. Otherwise return OpenAPI 3.1 'any' schema: {}.

    We check common keys used across systems.
    """
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
            schema = dict(schema)
            schema.pop("$schema", None)
            if "type" not in schema and "properties" in schema:
                schema["type"] = "object"
            return schema, True

    # OpenAPI 3.1: empty schema means "any type"
    return {}, False
