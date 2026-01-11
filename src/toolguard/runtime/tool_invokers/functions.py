from typing import Any, Callable, Dict, List, Type, TypeVar
from toolguard.runtime.data_types import IToolInvoker


class ToolFunctionsInvoker(IToolInvoker):
    T = TypeVar("T")

    def __init__(self, funcs: List[Callable]) -> None:
        self._funcs_by_name = {func.__name__: func for func in funcs}

    def invoke(
        self, toolname: str, arguments: Dict[str, Any], return_type: Type[T]
    ) -> T:
        func = self._funcs_by_name.get(toolname)
        assert callable(func), f"Tool {toolname} was not found"
        return func(**arguments)
