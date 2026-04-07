"""Lightweight replacement for mellea's @generative decorator.

Builds a prompt from a function's name, signature, docstring, and bound
keyword arguments, then sends it to an I_TG_LLM backend and returns the
raw text response.
"""

import inspect
from typing import Any, Callable, Dict, List

from toolguard.buildtime.llm import I_TG_LLM


def _format_arg(func: Callable, key: str, val: Any) -> str:
    """Format a single argument line like mellea's Arguments component."""
    sig = inspect.signature(func)
    param = sig.parameters.get(key)
    if param and param.annotation is not inspect.Parameter.empty:
        param_type = param.annotation
    else:
        param_type = type(val)

    if param_type is str:
        display_val = f'"{val!s}"'
    else:
        display_val = str(val)

    return f"- {key}: {display_val}  (type: {param_type})"


def build_prompt(func: Callable, **kwargs: Any) -> str:
    """Build the same prompt that mellea's GenerativeSlot + TemplateFormatter produces."""
    sig_str = str(inspect.signature(func))
    docstring = inspect.getdoc(func) or "No documentation provided."

    lines = [
        "Your task is to imitate the output of the following function for the given arguments.",
        "Reply Nothing else but the output of the function.",
        "",
        "Function:",
        f"def {func.__name__}{sig_str}:",
        f'    """{docstring}"""',
    ]

    if kwargs:
        arg_lines = [_format_arg(func, k, v) for k, v in kwargs.items()]
        lines.append("")
        lines.append("Arguments:")
        lines.extend(arg_lines)

    return "\n".join(lines)


async def run_prompt(
    llm: I_TG_LLM,
    func: Callable,
    **kwargs: Any,
) -> str:
    """Build a prompt from *func*'s metadata + *kwargs*, send it to *llm*, return the response."""
    prompt = build_prompt(func, **kwargs)
    msg: Dict = {
        "role": "user",
        "content": [{"type": "text", "text": prompt}],
    }
    return await llm.generate([msg])
