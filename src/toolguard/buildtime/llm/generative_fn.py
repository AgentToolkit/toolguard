"""
Module for generating prompts that instruct an LLM to imitate function output.
"""

import inspect
from typing import (
    Any,
    Awaitable,
    Callable,
    Concatenate,
    Generic,
    ParamSpec,
    TypeVar,
    cast,
    get_origin,
)

from pydantic import BaseModel, TypeAdapter

from toolguard.buildtime.llm.i_tg_llm import I_TG_LLM

Params = ParamSpec("Params")
ReturnType = TypeVar("ReturnType")


class GenerativeFunction(Generic[Params, ReturnType]):
    """Wrapper for functions decorated with @generative."""

    def __init__(self, func: Callable[Params, ReturnType]) -> None:
        """Initialize with the original function."""
        self._func = func
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__

        # Create a new signature that includes llm as the first parameter
        original_sig = inspect.signature(func)
        llm_param = inspect.Parameter(
            "llm", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=I_TG_LLM
        )
        new_params = [llm_param] + list(original_sig.parameters.values())
        self.__signature__ = original_sig.replace(parameters=new_params)

    async def __call__(
        self, llm: I_TG_LLM, /, *args: Params.args, **kwargs: Params.kwargs
    ) -> ReturnType:
        """Generate and parse the function result using the provided LLM."""
        prompt = self._generate_prompt(*args, **kwargs)
        response = await llm.generate([{"role": "user", "content": prompt}])
        return self._parse_response(response)

    def _generate_prompt(self, *args: Params.args, **kwargs: Params.kwargs) -> str:
        """Generate a prompt for the function with given arguments."""
        return generate_function_imitation_prompt(self._func, *args, **kwargs)

    def _parse_response(self, response: str) -> ReturnType:
        """Parse raw LLM text into the wrapped function return type."""
        return_annotation = inspect.signature(self._func).return_annotation
        if return_annotation is inspect.Signature.empty:
            return response  # type: ignore[return-value]

        if return_annotation is str:
            return response  # type: ignore[return-value]

        if return_annotation is None or return_annotation is type(None):
            return None  # type: ignore[return-value]

        if return_annotation is bool:
            normalized = response.strip()
            if normalized == "True":
                return True  # type: ignore[return-value]
            if normalized == "False":
                return False  # type: ignore[return-value]
            raise ValueError(f"Cannot parse boolean response: {response!r}")

        if return_annotation in (int, float):
            return return_annotation(response.strip())  # type: ignore[return-value]

        if get_origin(return_annotation) is not None:
            return TypeAdapter(return_annotation).validate_json(response)

        if inspect.isclass(return_annotation) and issubclass(
            return_annotation, BaseModel
        ):
            return return_annotation.model_validate_json(response)  # type: ignore[return-value]

        return TypeAdapter(return_annotation).validate_json(response)


def serialize_argument(arg: Any) -> str:
    """
    Serialize a function argument to a string representation.

    Handles primitive types, Pydantic models, and other types.

    Args:
        arg: The argument to serialize

    Returns:
        str: String representation of the argument
    """
    if arg is None:
        return "None"
    elif isinstance(arg, bool):
        return str(arg)
    elif isinstance(arg, (int, float)):
        return str(arg)
    elif isinstance(arg, str):
        return repr(arg)
    elif isinstance(arg, BaseModel):
        # Pydantic model - serialize to JSON
        return arg.model_dump_json(indent=2)
    elif isinstance(arg, (list, tuple)):
        items = [serialize_argument(item) for item in arg]
        return f"[{', '.join(items)}]"
    elif isinstance(arg, dict):
        items = [f"{repr(k)}: {serialize_argument(v)}" for k, v in arg.items()]
        return f"{{{', '.join(items)}}}"
    else:
        # Fallback to repr for other types
        return repr(arg)


def generate_function_imitation_prompt(
    func: Callable, *args: Any, **kwargs: Any
) -> str:
    """
    Generate a prompt that instructs an LLM to imitate the output of a function.

    The prompt includes:
    1. Instructions to imitate the function output
    2. Function signature
    3. Function documentation
    4. Serialized function arguments

    Args:
        func: The function to generate a prompt for
        *args: Positional arguments to the function
        **kwargs: Keyword arguments to the function

    Returns:
        str: The generated prompt
    """
    # Start with instructions
    prompt_parts = [
        "Your task is to imitate the output of the following function for the given arguments.",
        "Reply Nothing else but the output of the function.",
        "",
    ]

    # Add function signature
    sig = inspect.signature(func)
    func_name = func.__name__
    prompt_parts.append("Function signature:")
    prompt_parts.append(f"def {func_name}{sig}:")
    prompt_parts.append("")

    # Add function documentation
    doc = inspect.getdoc(func)
    if doc:
        prompt_parts.append("Function documentation:")
        prompt_parts.append(doc)
        prompt_parts.append("")

    # Serialize arguments
    prompt_parts.append("Function arguments:")

    # Get parameter names from signature
    params = list(sig.parameters.keys())

    # Serialize positional arguments
    for i, arg in enumerate(args):
        if i < len(params):
            param_name = params[i]
            serialized = serialize_argument(arg)
            prompt_parts.append(f"- {param_name} = {serialized}")

    # Serialize keyword arguments
    for key, value in kwargs.items():
        serialized = serialize_argument(value)
        prompt_parts.append(f"{key} = {serialized}")

    return "\n".join(prompt_parts)


def generative(
    func: Callable[Params, ReturnType],
) -> Callable[Concatenate[I_TG_LLM, Params], Awaitable[ReturnType]]:
    """
    Decorator that transforms a function to require an LLM as the first parameter.

    The decorated function's signature changes from func(args) to async func(llm, args).
    When called, it generates a prompt instructing the LLM to imitate the original
    function's output for the given arguments.

    Example:
        @generative
        def add(a: int, b: int) -> int:
            '''Add two numbers.'''
            return a + b

        llm = MockLLM("5")
        result = await add(llm, 2, 3)  # Returns 5 (parsed from LLM response)

    Args:
        func: The function to decorate

    Returns:
        An async callable that takes (llm, *args, **kwargs) and returns Awaitable[ReturnType]
    """
    return cast(
        Callable[Concatenate[I_TG_LLM, Params], Awaitable[ReturnType]],
        GenerativeFunction(func),
    )
