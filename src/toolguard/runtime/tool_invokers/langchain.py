from typing import Any, Dict, List, Type, TypeVar
from langchain_core.tools import BaseTool

from toolguard.runtime.data_types import IToolInvoker


class LangchainToolInvoker(IToolInvoker):
    T = TypeVar("T")
    _tools: Dict[str, BaseTool]

    def __init__(self, tools: List[BaseTool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def invoke(
        self, toolname: str, arguments: Dict[str, Any], return_type: Type[T]
    ) -> T:
        tool = self._tools.get(toolname)
        if tool:
            return tool.invoke(arguments)
        raise ValueError(f"unknown tool {toolname}")
