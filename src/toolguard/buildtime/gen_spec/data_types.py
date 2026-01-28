from typing import Dict

from pydantic import BaseModel


class ToolInfoParam(BaseModel):
    type: str
    description: str | None
    required: bool


class ToolInfo(BaseModel):
    name: str
    summary: str
    description: str
    parameters: Dict[str, ToolInfoParam]
    signature: str
