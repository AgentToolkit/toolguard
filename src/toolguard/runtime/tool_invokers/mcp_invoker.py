from typing import Any, Dict, Type, TypeVar, cast

from fastmcp.client import Client
from toolguard.runtime.data_types import IToolInvoker

T = TypeVar("T")


class MCPToolInvoker(IToolInvoker):  # pylint: disable=too-few-public-methods
    """Tool invoker implementation for MCP (Model Context Protocol) servers.

    This invoker enables interaction with MCP servers through the fastmcp client,
    allowing tools to be invoked remotely via the MCP protocol.

    Args:
        client: An initialized fastmcp Client instance for communicating with the MCP server.
    """

    def __init__(self, client: Client) -> None:
        self._client = client

    async def invoke(
        self, toolname: str, arguments: Dict[str, Any], return_type: Type[T]
    ) -> T:
        result = await self._client.call_tool(name=toolname, arguments=arguments)
        return cast(T, result.data)
