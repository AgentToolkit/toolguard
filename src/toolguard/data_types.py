import json
import os
from pathlib import Path
from types import ModuleType
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Type

def to_md_bulltets(items: List[str])->str:
    s = ""
    for item in items:
        s+=f"* {item}\n"
    return s

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
    name: str
    description: str = Field(..., description="Policy item description")
    references: List[str] = Field(..., description="original text")
    compliance_examples: Optional[List[str]] = Field(..., description="Case example that complies with the policy")
    violation_examples: Optional[List[str]] = Field(..., description="Case example that violates the policy")

    def __str__(self) -> str:
        s = f"#### Policy item " + self.name + "\n"
        s += f"{self.description}\n"
        if self.compliance_examples:
            s += f"##### Positive examples\n{to_md_bulltets(self.compliance_examples)}"
        if self.violation_examples:
            s += f"##### Negative examples\n{to_md_bulltets(self.violation_examples)}"
        return s
        

class ToolPolicy(BaseModel):
    name: str
    policy_items: List[ToolPolicyItem]

class Domain(BaseModel):
    common: FileTwin
    types: FileTwin

    api_class_name: str
    api: FileTwin

    api_impl_class_name: str
    api_impl: FileTwin

class ToolGuardCodeResult(BaseModel):
    tool: ToolPolicy
    guard_fn_name: str
    guard_file: FileTwin
    item_guard_files: List[FileTwin|None]
    test_files: List[FileTwin|None]

class ToolGuardCodeGenerationResult(BaseModel):
    output_path: str
    domain: Domain
    tools: Dict[str, ToolGuardCodeResult]

    def save(self, directory: str, filename: str = "result.json") -> None:
        full_path = os.path.join(directory, filename)
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(self.model_dump(), f, indent=2)
    
    @staticmethod
    def load(directory: str, filename: str = "result.json") -> "ToolGuardCodeGenerationResult":
        full_path = os.path.join(directory, filename)
        with open(full_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return ToolGuardCodeGenerationResult(**data)

    def check_tool_call(self, tool_name:str, args: dict, messages: List):
        tool = self.tools.get(tool_name)
        assert tool, f"Unknown tool {tool_name}"

        guard_file = os.path.join(self.output_path, tool.guard_file.file_name)
        module = load_module_from_path(guard_file, file_to_module(tool.guard_file.file_name))
        guard_fn =find_function_in_module(module, tool.guard_fn_name)
        assert guard_fn "Guard not found"

        sig = inspect.signature(guard_fn)
        guard_args = {}
        for p_name, param in sig.parameters.items():
            if p_name == "args":
                if issubclass(param.annotation, BaseModel):
                    guard_args[p_name] = param.annotation.model_construct(**args)
                else:
                    guard_args[p_name] = args
            elif p_name == "history":
                guard_args[p_name] = ChatHistory(messages, None) #FIXME LLM
            elif p_name == "api":
                api_impl_file = os.path.join(self.output_path, self.domain.api_impl.file_name)
                module = load_module_from_path(api_impl_file, file_to_module(self.domain.api_impl.file_name))
                cls = find_class_in_module(module, self.domain.api_impl_class_name)
                assert cls
                guard_args[p_name] = cls()
        
        guard_fn(**guard_args)
    
class LLM(BaseModel):
    def generate(self, messages: List[Dict])->str:
        ...

class Litellm(LLM):
    model_name: str
    custom_provider: str

    def __init__(self, model_name: str, custom_provider: str = "azure") -> None:
        self.model_name=model_name
        self.custom_provider=custom_provider
        
    def generate(self, messages: List[Dict])->str:
        from litellm import completion
        resp = completion(
            messages=messages,
            model=self.model_name,
            custom_llm_provider= self.custom_provider)
        return resp.choices[0].message.content
    
def ask_llm(question:str, conversation: List[Dict], llm: LLM)->str:
    prompt = f"""You are given a question and an historical conversation between a user and an ai-agent.
Your task is to answer the question according to the conversation.

Conversation:
{json.dumps(conversation, indent=4)}

Question:
{question}
"""
    msg = {"role":"system", "content": prompt}
    return llm.generate([msg])

class ChatHistory:
    """Represents a history of chat messages and provides methods check if specific events already happened."""
    messages: List[Dict]
    llm: LLM

    def __init__(self, messages: List[Dict], llm: LLM) -> None:
        self.messages = messages
        self.llm = llm

    def ask(self, question:str)->str:
        """Asks a question using the chat history and returns the model's textual response.

        Args:
            question (str): The question to be asked. Example: "What cancellation reason type did the user provide: 'Health', 'Change of plans', 'Other'"

        Returns:
            str: The response generated by the language model.
        """
        return ask_llm(question, self.messages, self.llm)
    
    def ask_bool(self, question:str)->bool:
        """Asks a yes/no question and returns the response as a boolean.

        Args:
            question (str): The yes/no question to be asked. Example: "Did the user accepted the agent's proposal?"

        Returns:
            bool: The interpreted boolean response from the language model.
        """
        return bool(ask_llm(question, self.messages, self.llm))
    

    def did_tool_return_value(self, tool_name:str,expected_value)->bool:
        """Checks whether a specific tool was called in the chat history and validates if the expected value was returned
            Example: "did_tool_return_value("book_hotel",True) checks if the history shows calling the function book_hotel and if the returned value was true did_tool_return_value will return true else false
       

        Args:
            tool_name (str): The name of the tool to check for in the message history.
            expected_value: The expected value of the tool call.
            
            

        Returns:
            bool: True if the tool was called returning expected_value, False otherwise.
        """
        for msg in self.messages:
            if msg.get('tool_name') == tool_name and msg.get('content') == expected_value:
                return True
        return False

    def was_tool_called(self, tool_name: str) -> bool:
        """Checks whether a specific tool was called in the chat history.
        
		Args:
			tool_name (str): The name of the tool to check for in the message history.

		Returns:
			bool: True if the tool was called, False otherwise.
		"""
        for msg in self.messages:
            if msg.get('tool_name') == tool_name:
                return True
        return False


class PolicyViolationException(Exception):
    _msg: str
    def __init__(self, message:str):
        super().__init__(message)
        self._msg = message

    @property
    def message(self):
        return self._msg
    
def file_to_module(file_path:str):
    return file_path.removesuffix('.py').replace('/', '.')

import importlib.util
import inspect
import os

def load_module_from_path(file_path: str, py_path:str) -> ModuleType:
    module_name = file_to_module(file_path)
    spec = importlib.util.spec_from_file_location(module_name, os.path.join(py_path, file_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore
    return module

def find_function_in_module(module: ModuleType, function_name:str):
    func = getattr(module, function_name, None)
    if func is None or not inspect.isfunction(func):
        raise AttributeError(f"Function '{function_name}' not found in module '{module.__name__}'")
    return func

def find_class_in_module(module: ModuleType, class_name:str)-> Optional[Type]:
    cls = getattr(module, class_name, None)
    if isinstance(cls, type):
        return cls
    return None

