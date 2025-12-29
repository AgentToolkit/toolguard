import inspect
import json
import logging
import os
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Any, Callable, Dict, List, Literal, Optional, cast

logger = logging.getLogger(__name__)

DEBUG_DIR = "debug"
TESTS_DIR = "tests"
RESULTS_FILENAME = "result.json"
API_PARAM = "api"
ARGS_PARAM = "args"

class ToolInfo(BaseModel):
	name: str
	description: str
	parameters: Any
	signature: str
	full_description:str

	@classmethod
	def from_function(cls, fn: Callable) -> "ToolInfo":
		# Assumes @tool decorator from langchain_core https://python.langchain.com/docs/how_to/custom_tools/
		# or a plain function with doc string
		def doc_summary(doc:str): 
			paragraphs = [p.strip() for p in doc.split("\n\n") if p.strip()]
			return paragraphs[0] if paragraphs else ""
		
		fn_name = fn.name if hasattr(fn, 'name') else fn.__name__ # type: ignore
		sig =fn_name + str(inspect.signature(fn))
		full_desc = fn.description if hasattr(fn,'description') else fn.__doc__.strip() if fn.__doc__ else (inspect.getdoc(fn) or "") # type: ignore
		return cls(
            name=fn_name,
			description=doc_summary(full_desc),
			full_description = full_desc,
            parameters=fn.args_schema.model_json_schema() if hasattr(fn, 'args_schema') else inspect.getdoc(fn), # type: ignore
			signature=sig,
        )
    

class FileTwin(BaseModel):
    file_name: str
    content: str

    def save(self, folder: str) -> "FileTwin":
        full_path = os.path.join(folder, self.file_name)
        parent = Path(full_path).parent
        os.makedirs(parent, exist_ok=True)
        with open(full_path, "w") as file:
            file.write(self.content)
        return self

    def save_as(self, folder: str, file_name: str) -> "FileTwin":
        file_path = os.path.join(folder, file_name)
        with open(file_path, "w") as file:
            file.write(self.content)
        return FileTwin(file_name=file_name, content=self.content)

    @staticmethod
    def load_from(folder: str, file_path: str) -> "FileTwin":
        with open(os.path.join(folder, file_path), "r") as file:
            data = file.read()
            return FileTwin(file_name=file_path, content=data)
        
        
class ToolGuardSpecItem(BaseModel):
    name: str = Field(..., description="Policy item name")
    description: str = Field(..., description="Policy item description")
    references: List[str] = Field(..., description="original texts")
    compliance_examples: Optional[List[str]] = Field(
        ..., description="Example of cases that comply with the policy"
    )
    violation_examples: Optional[List[str]] = Field(
        ..., description="Example of cases that violate the policy"
    )
    skip: bool = False

    def to_md_bulltets(self, items: List[str]) -> str:
        s = ""
        for item in items:
            s += f"* {item}\n"
        return s

    def __str__(self) -> str:
        s = "#### Policy item " + self.name + "\n"
        s += f"{self.description}\n"
        if self.compliance_examples:
            s += f"##### Positive examples\n{self.to_md_bulltets(self.compliance_examples)}"
        if self.violation_examples:
            s += f"##### Negative examples\n{self.to_md_bulltets(self.violation_examples)}"
        return s


class ToolGuardSpec(BaseModel):
    tool_name: str = Field(..., description="Name of the tool")
    policy_items: List[ToolGuardSpecItem] = Field(
        ...,
        description="Policy items. All (And logic) policy items must hold whehn invoking the tool.",
    )


def load_tool_policy(file_path: str, tool_name: str) -> ToolGuardSpec:
    with open(file_path, "r") as file:
        d = json.load(file)
    d["tool_name"] = tool_name
    spec = ToolGuardSpec.model_validate(d) #load deep
    return spec

class Domain(BaseModel):
    app_name: str = Field(..., description="Application name")
    toolguard_common: FileTwin = Field(
        ..., description="Pydantic data types used by toolguard framework."
    )
    app_types: FileTwin = Field(
        ..., description="Data types defined used in the application API as payloads."
    )
    app_api_class_name: str = Field(..., description="Name of the API class name.")
    app_api: FileTwin = Field(
        ..., description="Python class (abstract) containing all the API signatures."
    )
    app_api_size: int = Field(..., description="Number of functions in the API")


class RuntimeDomain(Domain):
    app_api_impl_class_name: str = Field(
        ..., description="Python class (implementaton) class name."
    )
    app_api_impl: FileTwin = Field(
        ..., description="Python class containing all the API method implementations."
    )

    def get_definitions_only(self):
        return Domain.model_validate(self.model_dump())


class PolicyViolationException(Exception):
    _msg: str

    def __init__(self, message: str):
        super().__init__(message)
        self._msg = message

    @property
    def message(self):
        return self._msg
