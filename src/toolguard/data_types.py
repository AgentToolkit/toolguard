from abc import ABC, abstractmethod
import os
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Any, List, Optional

DEBUG_DIR = "debug"
TESTS_DIR = "tests"
RESULTS_FILENAME = "result.json"
HISTORY_PARAM = "history"
HISTORY_PARAM_TYPE = "ChatHistory"
API_PARAM = "api"

class FileTwin(BaseModel):
    file_name: str
    content: str

    def save(self, folder:str)->'FileTwin':
        full_path = os.path.join(folder, self.file_name)
        parent = Path(full_path).parent
        os.makedirs(parent, exist_ok=True)
        with open(full_path, "w") as file:
            file.write(self.content)
        return self

    def save_as(self, folder:str, file_name:str)->'FileTwin':
        file_path = os.path.join(folder, file_name)
        with open(file_path, "w") as file:
            file.write(self.content)
        return FileTwin(file_name=file_name, content=self.content)

    @staticmethod
    def load_from(folder:str, file_path:str)->'FileTwin':
        with open(os.path.join(folder, file_path), "r") as file:
            data = file.read()
            return FileTwin(
                file_name=file_path, 
                content=data
            )

class ToolPolicyItem(BaseModel):
    name: str = Field(..., description="Policy item name")
    description: str = Field(..., description="Policy item description")
    references: List[str] = Field(..., description="original texts")
    compliance_examples: Optional[List[str]] = Field(..., description="Example of cases that comply with the policy")
    violation_examples: Optional[List[str]] = Field(..., description="Example of cases that violate the policy")

    def to_md_bulltets(self, items: List[str])->str:
        s = ""
        for item in items:
            s+=f"* {item}\n"
        return s
    
    def __str__(self) -> str:
        s = f"#### Policy item " + self.name + "\n"
        s += f"{self.description}\n"
        if self.compliance_examples:
            s += f"##### Positive examples\n{self.to_md_bulltets(self.compliance_examples)}"
        if self.violation_examples:
            s += f"##### Negative examples\n{self.to_md_bulltets(self.violation_examples)}"
        return s

class ToolPolicy(BaseModel):
    tool_name: str = Field(..., description="Name of the tool")
    policy_items: List[ToolPolicyItem] = Field(..., description="Policy items. All (And logic) policy items must hold whehn invoking the tool.")

class Domain(BaseModel):
    app_name: str = Field(..., description="Application name")
    toolguard_common: FileTwin = Field(..., description="Pydantic data types used by toolguard framework.")
    app_types: FileTwin = Field(..., description="Data types defined used in the application API as payloads.")
    app_api_class_name: str = Field(..., description="Name of the API class name.")
    app_api: FileTwin = Field(..., description="Python class (abstract) containing all the API signatures.")
    app_api_size: int = Field(..., description="Number of functions in the API")

class RuntimeDomain(Domain):
    app_api_impl_class_name: str = Field(..., description="Python class (implementaton) class name.")
    app_api_impl: FileTwin = Field(..., description="Python class containing all the API method implementations.")

class ChatHistory(ABC):
    """Represents a history of chat messages and provides methods check if specific events already happened."""

    @abstractmethod
    def ask_bool(self, question:str)->bool:
        """
        Asks a yes/no question and returns the response as a boolean.

        Args:
            question (str): The yes/no question to be asked. Example: "Did the user accepted the agent's proposal?"

        Returns:
            bool: The interpreted boolean response from the language model.
        """
        pass
    
    @abstractmethod
    def did_tool_return_value(self, tool_name:str, expected_value:Any)->bool:
        """
        Checks whether a specific tool was called in the chat history and validates if the expected value was returned
            Example: "did_tool_return_value("book_hotel",True) checks if the history shows calling the function book_hotel and if the returned value was true did_tool_return_value will return true else false
        
        Args:
            tool_name (str): The name of the tool to check for in the message history.
            expected_value: The expected value of the tool call.
        
        Returns:
            bool: True if the tool was called returning expected_value, False otherwise.
        """
        pass

    @abstractmethod
    def was_tool_called(self, tool_name: str) -> bool:
        """
        Checks whether a specific tool was called in the chat history.
		Args:
			tool_name (str): The name of the tool to check for in the message history.
		Returns:
			bool: True if the tool was called, False otherwise.
		"""
        pass


class PolicyViolationException(Exception):
    _msg: str
    def __init__(self, message:str):
        super().__init__(message)
        self._msg = message

    @property
    def message(self):
        return self._msg
