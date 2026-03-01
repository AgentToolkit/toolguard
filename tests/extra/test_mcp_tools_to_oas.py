"""
E2E test for export_mcp_tools_as_openapi().

Spins up a real FastMCP HTTP server (in a background thread) populated with
the tau2 airline tool definitions imported directly from
``tau2.domains.airline.tools``, then calls the function-under-test and
asserts that every tool is present in the resulting OpenAPI spec with the
correct input schema properties.
"""

from __future__ import annotations

import socket
import threading
import time
from typing import Any

import pytest
import uvicorn
from fastmcp import FastMCP
from tau2.domains.airline.data_model import FlightDB
from tau2.domains.airline.tools import AirlineTools

from toolguard.extra.list_mcp_tools import MCPConnectionConfig, list_mcp_tools
from toolguard.extra.mcp_tools_to_oas import mcp_tools_to_openapi

# ---------------------------------------------------------------------------
# Build the FastMCP server from the real tau2 AirlineTools
# ---------------------------------------------------------------------------


def _build_airline_mcp() -> FastMCP:
    """
    Instantiate AirlineTools with an empty in-memory DB and register every
    public tool method on a FastMCP server.  No real data is needed because
    the server is only used to expose tool *schemas*, not to execute calls.
    """
    db = FlightDB(flights={}, users={}, reservations={})
    airline = AirlineTools(db)

    mcp = FastMCP("tau2-airline-test")

    # Register every method that carries the @is_tool decorator
    for attr_name in dir(airline):
        if attr_name.startswith("_"):
            continue
        method = getattr(airline, attr_name)
        if callable(method) and hasattr(method, "__tool__"):
            mcp.tool(method)

    return mcp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _free_port() -> int:
    """Return an OS-assigned free TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---------------------------------------------------------------------------
# Pytest fixture – ephemeral MCP HTTP server
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def mcp_server_url():
    """
    Start a FastMCP HTTP server in a background thread and yield its MCP URL.
    The server is shut down after the module's tests finish.
    """
    mcp = _build_airline_mcp()
    port = _free_port()
    host = "127.0.0.1"

    app = mcp.http_app(transport="streamable-http")

    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="warning",
    )
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait until the server is ready (up to 5 s)
    deadline = time.monotonic() + 5.0
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("FastMCP test server did not start in time")
        time.sleep(0.05)

    yield f"http://{host}:{port}/mcp"

    server.should_exit = True
    thread.join(timeout=5)


# ---------------------------------------------------------------------------
# Expected tool catalogue (derived from tau2 AirlineTools public API)
# ---------------------------------------------------------------------------

EXPECTED_TOOLS: dict[str, dict[str, Any]] = {
    "book_reservation": {
        "required_params": {
            "user_id",
            "origin",
            "destination",
            "flight_type",
            "cabin",
            "flights",
            "passengers",
            "payment_methods",
            "total_baggages",
            "nonfree_baggages",
            "insurance",
        },
    },
    "calculate": {
        "required_params": {"expression"},
    },
    "cancel_reservation": {
        "required_params": {"reservation_id"},
    },
    "get_flight_status": {
        "required_params": {"flight_number", "date"},
    },
    "get_reservation_details": {
        "required_params": {"reservation_id"},
    },
    "get_user_details": {
        "required_params": {"user_id"},
    },
    "list_all_airports": {
        "required_params": set(),
    },
    "search_direct_flight": {
        "required_params": {"origin", "destination", "date"},
    },
    "search_onestop_flight": {
        "required_params": {"origin", "destination", "date"},
    },
    "send_certificate": {
        "required_params": {"user_id", "amount"},
    },
    "transfer_to_human_agents": {
        "required_params": {"summary"},
    },
    "update_reservation_baggages": {
        "required_params": {
            "reservation_id",
            "total_baggages",
            "nonfree_baggages",
            "payment_id",
        },
    },
    "update_reservation_flights": {
        "required_params": {"reservation_id", "cabin", "flights", "payment_id"},
    },
    "update_reservation_passengers": {
        "required_params": {"reservation_id", "passengers"},
    },
}


# ---------------------------------------------------------------------------
# The test
# ---------------------------------------------------------------------------


def _collect_refs(node: Any) -> list[str]:
    """Recursively collect all $ref values from a JSON-schema node."""
    refs: list[str] = []
    if isinstance(node, list):
        for item in node:
            refs.extend(_collect_refs(item))
    elif isinstance(node, dict):
        if "$ref" in node:
            refs.append(node["$ref"])
        for v in node.values():
            refs.extend(_collect_refs(v))
    return refs


def _assert_oas_structure(
    oas: dict[str, Any],
    title: str,
    version: str,
) -> None:
    """Shared assertions for a well-formed OpenAPI 3.1 document."""
    assert oas["openapi"] == "3.1.0"
    assert oas["info"]["title"] == title
    assert oas["info"]["version"] == version
    assert "paths" in oas

    paths: dict[str, Any] = oas["paths"]

    for tool_name, expectations in EXPECTED_TOOLS.items():
        route = f"/{tool_name}"
        assert route in paths, f"Missing path for tool '{tool_name}'"

        post_op: dict[str, Any] = paths[route]["post"]

        assert post_op["operationId"] == tool_name, (
            f"operationId mismatch for '{tool_name}': {post_op['operationId']!r}"
        )

        assert "requestBody" in post_op, f"No requestBody for '{tool_name}'"
        req_body = post_op["requestBody"]
        assert req_body["required"] is True

        schema: dict[str, Any] = req_body["content"]["application/json"]["schema"]
        assert schema.get("type") == "object", (
            f"Input schema for '{tool_name}' is not type:object – got {schema.get('type')!r}"
        )

        props: dict[str, Any] = schema.get("properties", {})
        for param in expectations["required_params"]:
            assert param in props, (
                f"Parameter '{param}' missing from input schema of '{tool_name}'. "
                f"Found: {sorted(props.keys())}"
            )

        assert "200" in post_op["responses"], f"No 200 response for '{tool_name}'"

    expected_routes = {f"/{name}" for name in EXPECTED_TOOLS}
    actual_routes = set(paths.keys())
    assert actual_routes == expected_routes, (
        f"Unexpected routes in OAS.\n"
        f"  Extra  : {actual_routes - expected_routes}\n"
        f"  Missing: {expected_routes - actual_routes}"
    )

    all_refs = _collect_refs(oas["paths"])
    assert all_refs, "Expected at least some $ref values in the OAS paths"
    bad_refs = [r for r in all_refs if not r.startswith("#/components/schemas/")]
    assert not bad_refs, (
        f"Found $ref values that were NOT rewritten to #/components/schemas/...: {bad_refs}"
    )

    components = oas.get("components", {}).get("schemas", {})
    for expected_def in ("FlightInfo", "Passenger", "Payment"):
        assert expected_def in components, (
            f"Expected '{expected_def}' to be lifted into components.schemas. "
            f"Found: {sorted(components.keys())}"
        )


def test_list_mcp_tools(mcp_server_url: str) -> None:
    """list_mcp_tools() must return a non-empty list of raw tool dicts,
    one entry per expected tau2 airline tool."""
    cfg = MCPConnectionConfig(mcp_url=mcp_server_url)

    tools = list_mcp_tools(cfg)

    assert isinstance(tools, list), f"Expected list, got {type(tools)}"
    assert tools, "Expected at least one tool"

    tool_names = {t.get("name") for t in tools}
    for expected_name in EXPECTED_TOOLS:
        assert expected_name in tool_names, (
            f"Tool '{expected_name}' missing from list_mcp_tools() result. "
            f"Found: {sorted(tool_names)}"
        )


def test_mcp_tools_to_openapi(mcp_server_url: str) -> None:
    """mcp_tools_to_openapi() must produce a valid OpenAPI 3.1 document from
    a pre-fetched tool list, with the correct title and version."""
    cfg = MCPConnectionConfig(mcp_url=mcp_server_url)
    tools = list_mcp_tools(cfg)

    oas: dict[str, Any] = mcp_tools_to_openapi(
        tools, title="Tau2 Airline", version="0.1.0"
    )

    _assert_oas_structure(oas, title="Tau2 Airline", version="0.1.0")


# Made with Bob
