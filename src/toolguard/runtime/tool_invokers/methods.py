from typing import Any, Dict, Type, TypeVar
import inspect

from toolguard.runtime.data_types import IToolInvoker


class ToolMethodsInvoker(IToolInvoker):
    T = TypeVar("T")

    def __init__(self, object: object) -> None:
        self._obj = object

    async def invoke(
        self, toolname: str, arguments: Dict[str, Any], return_type: Type[T]
    ) -> T:
        mtd = getattr(self._obj, toolname)
        assert callable(mtd), f"Tool {toolname} was not found"
        result = mtd(**arguments)
        # Check if the result is awaitable (coroutine)
        if inspect.iscoroutine(result):
            return await result  # type: ignore[return-value]
        return result  # type: ignore[return-value]
