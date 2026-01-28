from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

import httpx


def export_mcp_tools_as_openapi(cfg: ExportConfig) -> Dict[str, Any]:
    """
    Returns an OpenAPI 3.1 spec where each MCP tool becomes:
      POST /tools/{tool_id}

    The spec includes vendor extensions:
      x-mcp-server-uuid: virtual server UUID
      x-mcp-endpoint: full MCP endpoint URL
      x-mcp-tool-id: tool id
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
        tool_name = _pick_mcp_tool_name(tool)
        tool_id = _pick_tool_id(tool)
        desc = _pick_tool_description(tool)
        input_schema = _pick_input_schema(tool)
        tool_display_name = _pick_tool_display_name(tool)
        tool_original_name = _pick_mcp_tool_original_name(tool)
        # Each tool is exported as a REST-like endpoint:
        # POST /tools/<tool_id>  { ...tool args... }
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
                            "examples": {
                                "example": {
                                    "value": {"__note__": "Fill with tool arguments"}
                                }
                            },
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Tool execution result (MCP CallToolResult-compatible)",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "additionalProperties": True,
                                }
                            }
                        },
                    }
                },
                # Vendor extensions so another system knows how to really execute
                "x-mcp-server-uuid": cfg.server_uuid,
                "x-mcp-endpoint": mcp_endpoint,
                "x-mcp-tool-id": tool_id,
                "x-mcp-upstream-meta": tool,  # optional: embed full raw tool metadata
            }
        }

    spec: dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {
            "title": cfg.title,
            "version": cfg.version,
            "description": (
                "Export of MCP Gateway tools as an OpenAPI contract. "
                "These paths represent tool invocations; execution should be routed via MCP using x-mcp-* fields."
            ),
        },
        "servers": [
            # This is the logical base URL for the exported REST-like paths:
            {"url": cfg.gateway_url.rstrip("/")},
        ],
        "paths": paths,
        "tags": [{"name": "mcp-tools"}],
        "components": {
            "securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}}
        },
        "security": [{"bearerAuth": []}],
        # Top-level vendor extensions for convenience
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
    gateway_url: str  # e.g. http://127.0.0.1:4444
    bearer_token: str  # MCPGATEWAY_BEARER_TOKEN
    server_uuid: str  # MCPGATEWAY_SERVER_UUID (virtual server)
    out_path: str = "mcp_tools_openapi.json"
    title: str = "MCP Gateway Tools"
    version: str = "0.1.0"


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _pick_mcp_tool_original_name(tool: dict[str, Any]) -> str:
    return tool.get("originalName") or "unknown-tool"


def _pick_mcp_tool_name(tool: dict[str, Any]) -> str:
    # Different gateway versions may use id/name fields.
    return tool.get("name") or "unknown-tool"


def _pick_tool_name(tool: dict[str, Any]) -> str:
    # Different gateway versions may use id/name fields.
    return tool.get("customName") or "unknown-tool"


def _pick_tool_id(tool: dict[str, Any]) -> str:
    # Different gateway versions may use id/name fields.
    return tool.get("id") or "unknown-tool"


def _pick_tool_display_name(tool: dict[str, Any]) -> str:
    # Different gateway versions may use id/name fields.
    return tool.get("displayName") or "unknown-tool"


def _pick_tool_description(tool: dict[str, Any]) -> str:
    return tool.get("description") or tool.get("summary") or ""


def _pick_input_schema(tool: dict[str, Any]) -> dict[str, Any]:
    """
    Try common fields. Gateways often expose one of:
      - inputSchema
      - input_schema
      - parameters (JSONSchema-ish)
      - schema
    If nothing exists, default to free-form object.
    """
    for key in ("inputSchema", "input_schema", "parameters", "schema"):
        schema = tool.get(key)
        if isinstance(schema, dict) and schema:
            # Ensure it looks like JSON Schema
            if "type" not in schema:
                schema = {"type": "object", **schema}
            return schema

    return {"type": "object", "additionalProperties": True}
