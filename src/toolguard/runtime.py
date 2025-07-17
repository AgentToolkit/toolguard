
from abc import ABC, abstractmethod
import inspect
import json
import os
from types import ModuleType
from typing import Dict, List, Optional, Type
from pydantic import BaseModel, PrivateAttr
import importlib.util
import inspect
import os

from toolguard.data_types import ChatHistory, FileTwin, RuntimeDomain, ToolPolicy

class LLM(ABC):
    @abstractmethod
    def generate(self, messages: List[Dict])->str:
        ...

def load(directory: str, filename: str = "result.json") -> "ToolGuardsCodeGenerationResult":
    full_path = os.path.join(directory, filename)
    with open(full_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return ToolGuardsCodeGenerationResult(**data)

class ToolGuardCodeResult(BaseModel):
    tool: ToolPolicy
    guard_fn_name: str
    guard_file: FileTwin
    item_guard_files: List[FileTwin|None]
    test_files: List[FileTwin|None]

class ToolGuardsCodeGenerationResult(BaseModel):
    domain: RuntimeDomain
    tools: Dict[str, ToolGuardCodeResult]
    _llm: LLM = PrivateAttr()

    @property
    def root_dir(self):
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.dirname(cur_dir)

    def save(self, directory: str, filename: str = "result.json") -> 'ToolGuardsCodeGenerationResult':
        full_path = os.path.join(directory, filename)
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(self.model_dump(), f, indent=2)
        return self

    def use_llm(self, llm: LLM):
        self._llm = llm
        return self
    
    def check_tool_call(self, tool_name:str, args: dict, messages: List):
        tool = self.tools.get(tool_name)
        if tool is None:
            return
        #assert tool, f"Unknown tool {tool_name}"

        guard_file = os.path.join(self.root_dir, tool.guard_file.file_name)
        module = load_module_from_path(guard_file, file_to_module(tool.guard_file.file_name))
        guard_fn =find_function_in_module(module, tool.guard_fn_name)
        assert guard_fn, "Guard not found"

        sig = inspect.signature(guard_fn)
        guard_args = {}
        for p_name, param in sig.parameters.items():
            if p_name == "args":
                if issubclass(param.annotation, BaseModel):
                    guard_args[p_name] = param.annotation.model_construct(**args)
                else:
                    guard_args[p_name] = args
            elif p_name == "history":
                guard_args[p_name] = ChatHistoryImpl(messages, self._llm)
            elif p_name == "api":
                api_impl_file = os.path.join(self.root_dir, self.domain.app_api_impl.file_name)
                module = load_module_from_path(api_impl_file, file_to_module(self.domain.app_api_impl.file_name))
                cls = find_class_in_module(module, self.domain.app_api_impl_class_name)
                assert cls
                guard_args[p_name] = cls()
        
        guard_fn(**guard_args)

def file_to_module(file_path:str):
    return file_path.removesuffix('.py').replace('/', '.')


def load_module_from_path(file_path: str, py_root:str) -> ModuleType:
    """
    Dynamically loads a Python module from a given file path, optionally relative to a base path.

    Args:
        file_path (str): The relative path to the Python file (e.g., 'my_module.py').
        py_path (str): The base directory where the file is located.
    """
    full_path = os.path.abspath(os.path.join(py_root, file_path))
    if not os.path.exists(full_path):
        raise ImportError(f"Module file does not exist: {full_path}")

    # Create a unique module name based on the file path
    module_name = os.path.splitext(os.path.basename(full_path))[0]

    spec = importlib.util.spec_from_file_location(module_name, full_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module spec from {full_path}")

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)  # type: ignore
    except Exception as e:
        raise ImportError(f"Failed to execute module '{module_name}': {e}")

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

class ChatHistoryImpl(ChatHistory):
    messages: List[Dict]
    llm: LLM

    def __init__(self, messages: List[Dict], llm: LLM) -> None:
        self.messages = messages
        self.llm = llm

    def ask(self, question:str)->str:
        return ask_llm(question, self.messages, self.llm)
    
    def ask_bool(self, question:str)->bool:
        return bool(ask_llm(question, self.messages, self.llm))

    def did_tool_return_value(self, tool_name:str,expected_value)->bool:
        for msg in self.messages:
            if msg.get('tool_name') == tool_name and msg.get('content') == expected_value:
                return True
        return False

    def was_tool_called(self, tool_name: str) -> bool:
        for msg in self.messages:
            if msg.get('tool_name') == tool_name:
                return True
        return False

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
