from __future__ import annotations

from dataclasses import dataclass
import os
import json
import re
from typing import Any, Dict, List, Optional

import httpx


@dataclass(frozen=True)
class MCPConnectionConfig:
    """Connection and authentication settings for fetching MCP tools."""

    gateway_tools_url: str = ""
    mcp_url: str = ""
    mcp_session_id: str = ""
    bearer_token: str = ""
    timeout_s: float = 30.0


# ============================================================
# Public API
# ============================================================


def list_mcp_tools(cfg: MCPConnectionConfig) -> List[Dict[str, Any]]:
    """Fetch and return the raw list of MCP tool descriptors.

    Depending on the configuration, tools are retrieved either from a gateway
    REST endpoint (``cfg.gateway_tools_url``) or directly from an MCP server
    (``cfg.mcp_url``).

    Args:
        cfg: Connection and authentication settings.

    Returns:
        A list of raw tool descriptor dicts as returned by the server.
    """
    if cfg.gateway_tools_url:
        return _fetch_tools_from_gateway(
            cfg.gateway_tools_url, cfg.bearer_token, cfg.timeout_s
        )
    if cfg.mcp_url:
        return _fetch_tools_from_mcp(cfg)
    raise ValueError("Provide either gateway_tools_url or mcp_url")


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


def _fetch_tools_from_gateway(
    url: str, bearer_token: str, timeout_s: float
) -> list[dict[str, Any]]:
    headers = _auth_headers(bearer_token)
    timeout = httpx.Timeout(timeout_s, connect=timeout_s)

    with httpx.Client(
        headers=headers, timeout=timeout, follow_redirects=True
    ) as client:
        r = client.get(url)
        r.raise_for_status()
        payload = r.json()

    if not isinstance(payload, list):
        raise TypeError(f"Expected list from {url}, got {type(payload)}")
    return payload


def _fetch_tools_from_mcp(cfg: MCPConnectionConfig) -> list[dict[str, Any]]:
    session_id = cfg.mcp_session_id or _mcp_initialize(
        cfg.mcp_url, cfg.bearer_token, cfg.timeout_s
    )

    req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    headers = _mcp_headers(cfg.bearer_token, session_id)

    timeout = httpx.Timeout(cfg.timeout_s, connect=cfg.timeout_s)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        with client.stream("POST", cfg.mcp_url, headers=headers, json=req) as r:
            r.raise_for_status()
            envelope = _read_first_jsonrpc_envelope(r)

    if envelope.get("error"):
        raise RuntimeError(f"MCP JSON-RPC error: {envelope['error']}")

    result = envelope.get("result")
    if not isinstance(result, dict):
        raise TypeError(f"Expected envelope.result dict, got {type(result)}")

    tools = result.get("tools")
    if not isinstance(tools, list):
        raise TypeError(
            f"Expected result.tools list from MCP tools/list, got {type(tools)}"
        )

    return tools


def _read_first_jsonrpc_envelope(resp: httpx.Response) -> dict[str, Any]:
    ctype = (resp.headers.get("content-type") or "").lower()

    if "text/event-stream" in ctype:
        for line in resp.iter_lines():
            if not line:
                continue
            line = line.strip()
            if not line.startswith("data:"):
                continue
            raw = line[len("data:") :].strip()
            try:
                obj = json.loads(raw)
            except Exception:
                continue
            if isinstance(obj, dict):
                return obj
        raise RuntimeError("Failed to parse SSE response (no JSON data lines).")
    else:
        obj = resp.json()

    if not isinstance(obj, dict):
        raise TypeError(f"Expected JSON-RPC envelope dict, got {type(obj)}")
    return obj


def _mcp_initialize(mcp_url: str, bearer_token: str, timeout_s: float) -> str:
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "openapi-exporter", "version": "0"},
        },
    }
    headers = _mcp_headers(bearer_token, None)

    timeout = httpx.Timeout(timeout_s, connect=timeout_s)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        with client.stream("POST", mcp_url, headers=headers, json=req) as r:
            r.raise_for_status()

            sid = (
                r.headers.get("mcp-session-id")
                or r.headers.get("Mcp-Session-Id")
                or r.headers.get("MCP-SESSION-ID")
                or ""
            )
            if sid:
                return sid

            ctype = (r.headers.get("content-type") or "").lower()
            if "text/event-stream" in ctype:
                for line in r.iter_lines():
                    if not line:
                        continue
                    line = line.strip()
                    if not line.startswith("data:"):
                        continue
                    raw = line[len("data:") :].strip()
                    try:
                        envelope = json.loads(raw)
                    except Exception:
                        continue

                    if isinstance(envelope, dict) and envelope.get("error"):
                        raise RuntimeError(f"MCP JSON-RPC error: {envelope['error']}")

                    result = (
                        envelope.get("result") if isinstance(envelope, dict) else None
                    )
                    if isinstance(result, dict):
                        sid2 = (
                            result.get("sessionId")
                            or result.get("session_id")
                            or result.get("mcpSessionId")
                            or ""
                        )
                        if sid2:
                            return sid2

            raise RuntimeError(
                "Could not determine MCP session id; provide mcp_session_id explicitly."
            )


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
    """
    For each schema that contains a TOP-LEVEL "$defs":
      - move each $defs entry into components.schemas
      - remove "$defs" from the schema in-place
      - recursively rewrite every "$ref": "#/$defs/<Name>" anywhere in the
        schema tree to "$ref": "#/components/schemas/<Name>"

    This is the only manipulation needed when gateway schemas are otherwise fine.
    """

    def _rewrite_refs(node: Any) -> Any:
        """Recursively rewrite #/$defs/... refs to #/components/schemas/..."""
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


def _auth_headers(token: str) -> dict[str, str]:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _mcp_headers(token: str, session_id: Optional[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    headers["Content-Type"] = "application/json"
    headers["Accept"] = "application/json, text/event-stream"
    if session_id:
        headers["mcp-session-id"] = session_id
    return headers


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
