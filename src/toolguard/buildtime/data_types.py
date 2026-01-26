from typing import Callable, Dict
from pydantic import BaseModel
import inspect


class ToolInfoParam(BaseModel):
    type: str
    description: str | None
    required: bool


class ToolInfo(BaseModel):
    name: str
    description: str
    parameters: Dict[str, ToolInfoParam]
    signature: str

    @classmethod
    def from_function(cls, fn: Callable) -> "ToolInfo":
        # Assumes @tool decorator from langchain_core https://python.langchain.com/docs/how_to/custom_tools/
        # or a plain function with doc string
        def doc_summary(doc: str):
            paragraphs = [p.strip() for p in doc.split("\n\n") if p.strip()]
            return paragraphs[0] if paragraphs else ""

        fn_name = fn.name if hasattr(fn, "name") else fn.__name__  # type: ignore
        sig = fn_name + str(inspect.signature(fn))
        full_desc = (
            fn.description
            if hasattr(fn, "description")
            else fn.__doc__.strip()
            if fn.__doc__
            else (inspect.getdoc(fn) or "")
        )  # type: ignore
        return ToolInfo(
            name=fn_name,
            description=doc_summary(full_desc),
            parameters=fn.args_schema.model_json_schema()
            if hasattr(fn, "args_schema")
            else inspect.getdoc(fn),  # type: ignore
            signature=sig,
        )
