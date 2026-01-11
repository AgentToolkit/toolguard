from typing import Any, Dict, Type, TypeVar
from toolguard.runtime.data_types import IToolInvoker


class ToolMethodsInvoker(IToolInvoker):
    T = TypeVar("T")

    def __init__(self, object: object) -> None:
        self._obj = object

    def invoke(
        self, toolname: str, arguments: Dict[str, Any], return_type: Type[T]
    ) -> T:
        mtd = getattr(self._obj, toolname)
        assert callable(mtd), f"Tool {toolname} was not found"
        return mtd(**arguments)
