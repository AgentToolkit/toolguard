from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import json
import re
from typing import Any, Dict, Tuple, Optional

import httpx


# ============================================================
# Public API
# ============================================================


def export_mcp_tools_as_openapi(cfg: "ExportConfig") -> Dict[str, Any]:
    """
    Minimal OpenAPI 3.1 export (your requested variant):
      ✅ build paths
      ✅ keep request/response schemas (as returned by MCP/Gateway + your description-enrichment)
      ✅ lift $defs -> components.schemas ONLY if they exist, and rewrite refs "#/$defs/X" accordingly

    No global schema dedupe / hashing / allOf.
    No "Root indirection" aliases.
    """
    tools = _fetch_tools(cfg)

    paths: dict[str, Any] = {}
    components_schemas: dict[str, Any] = {}

    for tool in tools:
        tool_name = _pick_mcp_tool_name(tool)
        tool_desc = _pick_tool_description(tool)
        summary = _pick_tool_summary(tool)

        input_schema = _normalize_schema(_pick_input_schema(tool))
        input_schema = _merge_param_descriptions_into_schema(
            schema=input_schema, tool=tool
        )

        output_schema, output_found = _pick_output_schema(tool)
        if output_found:
            output_schema = _normalize_schema(output_schema)
            output_schema = _merge_result_descriptions_into_schema(
                schema=output_schema, tool=tool
            )
        else:
            output_schema = {}  # OpenAPI 3.1 "any"

        req_schema_name = _schema_name(tool_name, "Request")
        resp_schema_name = _schema_name(tool_name, "Response")

        components_schemas[req_schema_name] = input_schema
        components_schemas[resp_schema_name] = output_schema

        route = f"/tools/{tool_name}"
        paths[route] = {
            "post": {
                "operationId": tool_name,
                "summary": summary or tool_name,
                "description": (tool_desc or "").strip(),
                "tags": ["mcp-tools"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": f"#/components/schemas/{req_schema_name}"
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": _pick_output_description(tool),
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": f"#/components/schemas/{resp_schema_name}"
                                }
                            }
                        },
                    }
                },
            }
        }

    # Only do the one normalization step you actually need:
    # lift local $defs -> components.schemas and rewrite "#/$defs/..." refs.
    components_schemas = _lift_defs_to_components(components_schemas)

    return {
        "openapi": "3.1.0",
        "info": {
            "title": cfg.title,
            "version": cfg.version,
            "description": (
                "OpenAPI export of MCP tools metadata. "
                "Contains only operation descriptions and input/output schemas to support code generation."
            ),
        },
        "paths": paths,
        "tags": [{"name": "mcp-tools"}],
        "components": {"schemas": components_schemas},
        "x-generated-at": datetime.now(timezone.utc).isoformat(),
    }


def export_mcp_tools_as_openapi_json_file(
    cfg: "ExportConfig", out_path: str | Path
) -> Path:
    spec = export_mcp_tools_as_openapi(cfg)

    out_path = Path(out_path).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    out_path.write_text(
        json.dumps(spec, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return out_path


# ============================================================
# Configuration
# ============================================================


@dataclass(frozen=True)
class ExportConfig:
    title: str = "MCP Tools"
    version: str = "0.1.0"

    gateway_tools_url: str = ""
    mcp_url: str = ""
    mcp_session_id: str = ""
    bearer_token: str = ""
    timeout_s: float = 30.0


# ============================================================
# Fetch Tools (connection logic kept from your working file)
# ============================================================


def _fetch_tools(cfg: ExportConfig) -> list[dict[str, Any]]:
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


def _fetch_tools_from_mcp(cfg: ExportConfig) -> list[dict[str, Any]]:
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

    return [_normalize_mcp_tool(t) for t in tools]


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


def _normalize_mcp_tool(t: dict[str, Any]) -> dict[str, Any]:
    out = dict(t)
    out.setdefault("displayName", out.get("name"))
    out.setdefault("originalName", out.get("name"))
    out.setdefault("id", out.get("name"))
    return out


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


def _pick_output_schema(tool: dict[str, Any]) -> Tuple[dict[str, Any], bool]:
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
            return dict(schema), True
    return {}, False


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
# Schema normalization & enrichment
# ============================================================


def _normalize_schema(schema: dict[str, Any]) -> dict[str, Any]:
    s = dict(schema or {})
    s.pop("$schema", None)
    if "type" not in s and isinstance(s.get("properties"), dict):
        s["type"] = "object"
    return s


def _merge_param_descriptions_into_schema(
    schema: dict[str, Any], tool: dict[str, Any]
) -> dict[str, Any]:
    s = dict(schema or {})
    if s.get("type") != "object":
        return s

    props = s.get("properties")
    if not isinstance(props, dict):
        props = {}
        s["properties"] = props

    candidates = (
        tool.get("params"),
        tool.get("parameters"),
        tool.get("inputParameters"),
        tool.get("arguments"),
    )

    for cand in candidates:
        if isinstance(cand, list):
            for item in cand:
                if not isinstance(item, dict):
                    continue
                name = item.get("name")
                if not name:
                    continue

                prop = props.get(name)
                if not isinstance(prop, dict):
                    prop = {}
                    props[name] = prop

                if "description" not in prop and item.get("description"):
                    prop["description"] = str(item["description"])

                item_schema = item.get("schema")
                if isinstance(item_schema, dict) and item_schema:
                    for k, v in _normalize_schema(item_schema).items():
                        prop.setdefault(k, v)

        elif isinstance(cand, dict):
            for name, item in cand.items():
                if not name:
                    continue

                prop = props.get(name)
                if not isinstance(prop, dict):
                    prop = {}
                    props[name] = prop

                if isinstance(item, dict):
                    if "description" not in prop and item.get("description"):
                        prop["description"] = str(item["description"])

                    item_schema = item.get("schema")
                    if isinstance(item_schema, dict) and item_schema:
                        for k, v in _normalize_schema(item_schema).items():
                            prop.setdefault(k, v)

    return s


def _merge_result_descriptions_into_schema(
    schema: dict[str, Any], tool: dict[str, Any]
) -> dict[str, Any]:
    s = dict(schema or {})
    if s.get("type") != "object":
        return s

    props = s.get("properties")
    if not isinstance(props, dict):
        props = {}
        s["properties"] = props

    candidates = (
        tool.get("outputFields"),
        tool.get("outputParameters"),
        tool.get("resultFields"),
        tool.get("result"),
    )

    for cand in candidates:
        if isinstance(cand, list):
            for item in cand:
                if not isinstance(item, dict):
                    continue
                name = item.get("name")
                if not name:
                    continue

                prop = props.get(name)
                if not isinstance(prop, dict):
                    prop = {}
                    props[name] = prop

                if "description" not in prop and item.get("description"):
                    prop["description"] = str(item["description"])

                item_schema = item.get("schema")
                if isinstance(item_schema, dict) and item_schema:
                    for k, v in _normalize_schema(item_schema).items():
                        prop.setdefault(k, v)

        elif isinstance(cand, dict):
            for name, item in cand.items():
                if not name:
                    continue

                prop = props.get(name)
                if not isinstance(prop, dict):
                    prop = {}
                    props[name] = prop

                if isinstance(item, dict):
                    if "description" not in prop and item.get("description"):
                        prop["description"] = str(item["description"])

                    item_schema = item.get("schema")
                    if isinstance(item_schema, dict) and item_schema:
                        for k, v in _normalize_schema(item_schema).items():
                            prop.setdefault(k, v)

    return s


# ============================================================
# Minimal $defs lifting (only if present)
# ============================================================


def _lift_defs_to_components(components: dict[str, Any]) -> dict[str, Any]:
    """
    For each component schema that contains a TOP-LEVEL "$defs":
      - move each $defs entry into components.schemas as:
          <Owner>_def_<DefName>
      - remove "$defs" from the owner schema
      - rewrite "$ref": "#/$defs/<DefName>" anywhere inside that owner schema
        to "$ref": "#/components/schemas/<Owner>_def_<DefName>"

    This is the only manipulation needed when gateway schemas are otherwise fine.
    """
    out: dict[str, Any] = dict(components)

    # owner -> {defName -> newComponentName}
    def_map: dict[str, dict[str, str]] = {}

    # 1) Lift
    for owner, schema in list(out.items()):
        if not isinstance(schema, dict):
            continue
        defs = schema.get("$defs")
        if not isinstance(defs, dict) or not defs:
            continue

        owner_map: dict[str, str] = {}
        used = set(out.keys())

        for def_name, def_schema in defs.items():
            base = f"{owner}_def_{_sanitize_component_name(str(def_name))}"
            new_name = _unique_component_name(base, used)
            used.add(new_name)
            out[new_name] = def_schema
            owner_map[str(def_name)] = new_name

        def_map[owner] = owner_map

        schema2 = dict(schema)
        schema2.pop("$defs", None)
        out[owner] = schema2

    # 2) Rewrite refs within each owner context
    def rewrite(node: Any, owner: str) -> Any:
        if isinstance(node, list):
            return [rewrite(x, owner) for x in node]
        if not isinstance(node, dict):
            return node

        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/$defs/"):
            def_name = ref.split("/", 3)[-1]
            target = def_map.get(owner, {}).get(def_name)
            if target:
                new_node = dict(node)  # preserve siblings like "description"
                new_node["$ref"] = f"#/components/schemas/{target}"
                return new_node

        return {k: rewrite(v, owner) for k, v in node.items()}

    for owner, schema in list(out.items()):
        if owner in def_map:  # only need owner-aware rewriting if it had defs
            out[owner] = rewrite(schema, owner)

    return out


# ============================================================
# Naming helpers
# ============================================================


def _schema_name(tool_name: str, suffix: str) -> str:
    # e.g. "clinic-upstream-add-user" -> "clinic_upstream_add_userRequest"
    base = re.sub(r"[^A-Za-z0-9_]+", "_", tool_name).strip("_")
    return f"{base or 'Tool'}{suffix}"


def _sanitize_component_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^A-Za-z0-9_]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "Schema"


def _unique_component_name(base: str, used: set[str]) -> str:
    if base not in used:
        return base
    i = 2
    while f"{base}_{i}" in used:
        i += 1
    return f"{base}_{i}"


# ============================================================
# HTTP helpers
# ============================================================


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


# ============================================================
# Example usage
# ============================================================

if __name__ == "__main__":
    cfg = ExportConfig(
        gateway_tools_url="http://127.0.0.1:4444/tools",
        bearer_token=os.environ.get("TOKEN", ""),
        title="My MCP Tools",
        version="1.0.0",
    )
    out_file = export_mcp_tools_as_openapi_json_file(
        cfg, "./out/gateway_mcp_tools_openapi_direct.json"
    )
    print(f"Wrote OpenAPI JSON to: {out_file}")
