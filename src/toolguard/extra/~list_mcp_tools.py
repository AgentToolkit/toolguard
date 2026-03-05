from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Dict, List, Optional
import uuid

import httpx


@dataclass(frozen=True)
class MCPConnectionConfig:
    """Connection and authentication settings for fetching MCP tools."""

    gateway_tools_url: str = ""
    mcp_url: str = ""
    mcp_session_id: str = ""
    bearer_token: str = ""
    timeout_s: float = 30.0


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

    req = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tools/list",
        "params": {},
    }
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
        "id": str(uuid.uuid4()),
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


# Made with Bob
