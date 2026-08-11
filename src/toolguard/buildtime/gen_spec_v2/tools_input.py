"""Normalizing every accepted tool-description shape into ``ToolInfo``.

v2 accepts what v1 accepts — callables or an OpenAPI dict — plus a plain
``list[ToolInfo]``, which is what a caller holding MCP tool definitions
already has. v1's ``_tools_to_tool_infos`` documents that branch but raises
on it; implementing it here keeps v1 untouched.
"""

from typing import Any, Callable, Dict, List, Sequence, Union, cast

from toolguard.buildtime.gen_spec.data_types import ToolInfo
from toolguard.buildtime.gen_spec.fn_to_toolinfo import function_to_toolInfo
from toolguard.buildtime.gen_spec.oas_to_toolinfo import openapi_to_toolinfos
from toolguard.buildtime.utils.open_api import OpenAPI

TOOLS_V2 = Union[Dict[str, Any], Sequence[Union[Callable, ToolInfo]]]


def to_tool_infos(tools: TOOLS_V2) -> List[ToolInfo]:
    """Convert ``tools`` to ``ToolInfo``s, preserving the caller's order.

    Accepts an OpenAPI spec dict, or a sequence mixing callables and
    ``ToolInfo``s. Raises ``ValueError`` on an empty sequence — generating
    specs for no tools is always a caller mistake — and
    ``NotImplementedError`` for an element that is neither.
    """
    if isinstance(tools, dict):
        return openapi_to_toolinfos(OpenAPI.model_validate(tools))

    if isinstance(tools, (list, tuple)):
        if not tools:
            raise ValueError("No tools supplied")
        infos: List[ToolInfo] = []
        for tool in tools:
            if isinstance(tool, ToolInfo):
                infos.append(tool)
            elif callable(tool):
                infos.append(function_to_toolInfo(cast(Callable, tool)))
            else:
                raise NotImplementedError(
                    f"Unsupported tool description: {type(tool).__name__}"
                )
        return infos

    raise NotImplementedError(f"Unsupported tools input: {type(tools).__name__}")
