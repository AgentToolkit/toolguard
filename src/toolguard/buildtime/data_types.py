from typing import Any, Callable, Dict, List

from langchain_core.tools import BaseTool


OPEN_API = Dict[str, Any]
TOOLS = List[Callable] | List[BaseTool] | OPEN_API
