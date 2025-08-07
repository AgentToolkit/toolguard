
from abc import ABC, abstractmethod
import inspect
import json
import os
from types import ModuleType
from typing import Any, Dict, List, Optional, Type, Callable, TypeVar
from pydantic import BaseModel, PrivateAttr
import importlib.util
import inspect
import os

import functools
from rt_toolguard.data_types import API_PARAM, HISTORY_PARAM, RESULTS_FILENAME, ChatHistory, FileTwin, RuntimeDomain, ToolPolicy

class LLM(ABC):
    @abstractmethod
    def generate(self, messages: List[Dict])->str:
        ...

def load_toolguards(directory: str, filename: str = RESULTS_FILENAME) -> "ToolGuardsCodeGenerationResult":
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
    _guards: Dict[str, Callable] = PrivateAttr()
    
    def model_post_init(self, __context):
        self._llm = None # type: ignore
        self._guards = {}
        for tool_name, tool_result in self.tools.items():
            module = load_module_from_path(tool_result.guard_file.file_name, self.root_dir)
            guard_fn =find_function_in_module(module, tool_result.guard_fn_name)
            assert guard_fn, "Guard not found"
            self._guards[tool_name] = guard_fn

    @property
    def root_dir(self):
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.dirname(cur_dir)

    def save(self, directory: str, filename: str = RESULTS_FILENAME) -> 'ToolGuardsCodeGenerationResult':
        full_path = os.path.join(directory, filename)
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(self.model_dump(), f, indent=2)
        return self

    def use_llm(self, llm: LLM):
        self._llm = llm
        return self
    
    def _make_args(self, guard_fn:Callable, args: dict, messages: List, delegate:Any)->Dict[str, Any]:
        sig = inspect.signature(guard_fn)
        guard_args = {}
        for p_name, param in sig.parameters.items():
            if p_name == HISTORY_PARAM:
                guard_args[p_name] = ChatHistoryImpl(messages, self._llm)
            elif p_name == API_PARAM:
                module = load_module_from_path(self.domain.app_api_impl.file_name, self.root_dir)
                cls = find_class_in_module(module, self.domain.app_api_impl_class_name)
                assert cls, f"class {self.domain.app_api_impl_class_name} not found in {self.domain.app_api_impl.file_name}"
                guard_args[p_name] = cls(delegate)
            else:
                arg = args.get(p_name)
                if inspect.isclass(param.annotation) and issubclass(param.annotation, BaseModel):
                    guard_args[p_name] = param.annotation.model_construct(arg)
                else:
                    guard_args[p_name] = arg
        return guard_args

    def check_toolcall(self, tool_name:str, args: dict, messages: List, delegate: Any):
        guard_fn = self._guards.get(tool_name)
        if guard_fn is None: #No guard assigned to this tool
            return
        guard_fn(**self._make_args(guard_fn, args, messages, delegate))

def file_to_module(file_path:str):
    return file_path.removesuffix('.py').replace('/', '.')

def load_module_from_path(file_path: str, py_root:str) -> ModuleType:
    full_path = os.path.abspath(os.path.join(py_root, file_path))
    if not os.path.exists(full_path):
        raise ImportError(f"Module file does not exist: {full_path}")

    module_name = file_to_module(file_path)

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



T = TypeVar("T")
def guard_methods(obj: T, guards_folder: str) -> T:
    """Wraps all public bound methods of the given instance using the given wrapper."""
    for attr_name in dir(obj):
        if attr_name.startswith("_"):
            continue
        attr = getattr(obj, attr_name)
        if callable(attr):
            wrapped = guard_before_call(guards_folder)(attr)
            setattr(obj, attr_name, wrapped)
    return obj

def guard_before_call(guards_folder: str) -> Callable[[Callable], Callable]:
    """Decorator factory that logs function calls to the given logfile."""
    toolguards = load_toolguards(guards_folder)
    llm = Litellm(model_name="ASASA", custom_provider="azure") #FIXME example
    toolguards.use_llm(llm)
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            api_object = func.__self__ # type: ignore
            toolguards.check_toolcall(func.__name__, kwargs, [], api_object)
            return func(*args, **kwargs)
        return wrapper  # type: ignore
    return decorator
