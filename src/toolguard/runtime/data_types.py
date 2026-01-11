from typing import Any, Dict, List, Type, TypeVar
import json
import os
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError
from abc import ABC, abstractmethod


API_PARAM = "api"
ARGS_PARAM = "args"
RESULTS_FILENAME = Path("result.json")


class FileTwin(BaseModel):
    file_name: Path
    content: str

    def save(self, folder: str | Path) -> "FileTwin":
        full_path = Path(folder) / self.file_name
        parent = full_path.parent
        os.makedirs(parent, exist_ok=True)
        with open(full_path, "w") as file:
            file.write(self.content)
        return self

    def save_as(self, folder: str | Path, file_name: str | Path) -> "FileTwin":
        file_path = Path(folder) / file_name
        with open(file_path, "w") as file:
            file.write(self.content)
        return FileTwin(file_name=Path(file_name), content=self.content)

    @staticmethod
    def load_from(folder: str | Path, file_path: str | Path) -> "FileTwin":
        with open(Path(folder) / file_path, "r") as file:
            data = file.read()
            return FileTwin(file_name=Path(file_path), content=data)


class ToolGuardSpecItem(BaseModel):
    name: str = Field(..., description="Policy item name")
    description: str = Field(..., description="Policy item description")
    references: List[str] = Field(default_factory=list, description="original texts")
    compliance_examples: List[str] = Field(
        default_factory=list, description="Example of cases that comply with the policy"
    )
    violation_examples: List[str] = Field(
        default_factory=list, description="Example of cases that violate the policy"
    )
    skip: bool = False
    _debug: Dict = {}

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
    _debug: Dict = {}

    @classmethod
    def load(cls, file_path: str | Path) -> "ToolGuardSpec":
        try:
            with open(file_path, "r") as file:
                d = json.load(file)
            return ToolGuardSpec.model_validate(d)  # load deep
        except ValidationError as e:
            raise ValueError(f"Invalid tool spec in {file_path}") from e


class Domain(BaseModel):
    app_name: str = Field(..., description="Application name")
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


class ToolGuardCodeResult(BaseModel):
    tool: ToolGuardSpec
    guard_fn_name: str
    guard_file: FileTwin
    item_guard_files: List[FileTwin | None]
    test_files: List[FileTwin | None]


class ToolGuardsCodeGenerationResult(BaseModel):
    out_dir: Path
    domain: RuntimeDomain
    tools: Dict[str, ToolGuardCodeResult]

    def save(
        self, directory: Path, filename: Path = RESULTS_FILENAME
    ) -> "ToolGuardsCodeGenerationResult":
        full_path = directory / filename
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2, default=str)
        return self

    @classmethod
    def load(
        cls, directory: str | Path, filename: str | Path = RESULTS_FILENAME
    ) -> "ToolGuardsCodeGenerationResult":
        full_path = Path(directory) / filename
        try:
            with open(full_path, "r") as file:
                d = json.load(file)
            return ToolGuardsCodeGenerationResult.model_validate(d)  # load deep
        except ValidationError as e:
            raise ValueError(f"Invalid tool spec in {full_path}") from e


class PolicyViolationException(Exception):
    _msg: str

    def __init__(self, message: str):
        super().__init__(message)
        self._msg = message

    @property
    def message(self):
        return self._msg


class IToolInvoker(ABC):
    T = TypeVar("T")

    @abstractmethod
    def invoke(
        self, toolname: str, arguments: Dict[str, Any], return_type: Type[T]
    ) -> T: ...
