import inspect
import re
from typing import Callable, Dict, get_type_hints

from toolguard.buildtime.gen_spec.data_types import ToolInfo, ToolInfoParam


def function_to_toolInfo(fn: Callable) -> ToolInfo:
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
    params: Dict[str, ToolInfoParam] = extract_fn_params(fn)
    return ToolInfo(
        name=fn_name,
        summary=doc_summary(full_desc),
        description=full_desc,
        parameters=params,
        signature=sig,
    )


def extract_fn_params(fn: Callable) -> Dict[str, ToolInfoParam]:
    """Extract parameter information from a function's signature and docstring.

    Args:
        fn: The function to extract parameters from

    Returns:
        Dictionary mapping parameter names to ToolInfoParam objects
    """
    # Get type hints from function signature
    try:
        type_hints = get_type_hints(fn)
    except Exception:
        type_hints = {}

    # Get function signature
    sig = inspect.signature(fn)

    # Parse docstring to extract parameter descriptions
    docstring = inspect.getdoc(fn) or ""
    param_descriptions = _parse_param_descriptions(docstring)

    # Build parameter dictionary
    params: Dict[str, ToolInfoParam] = {}
    for param_name, param in sig.parameters.items():
        # Skip self, cls, *args, **kwargs
        if param_name in ("self", "cls") or param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue

        # Get type annotation
        param_type = type_hints.get(param_name, param.annotation)
        if param_type == inspect.Parameter.empty:
            type_str = "Any"
        else:
            type_str = _type_to_string(param_type)

        # Get description from docstring
        description = param_descriptions.get(param_name)

        # Determine if required (no default value)
        required = param.default == inspect.Parameter.empty

        params[param_name] = ToolInfoParam(
            type=type_str, description=description, required=required
        )

    return params


def _parse_param_descriptions(docstring: str) -> Dict[str, str]:
    """Parse parameter descriptions from Google-style or Sphinx-style docstrings.

    Args:
        docstring: The docstring to parse

    Returns:
        Dictionary mapping parameter names to their descriptions
    """
    descriptions: Dict[str, str] = {}

    if not docstring:
        return descriptions

    lines = docstring.split("\n")

    # Find Args: section (Google style)
    in_args_section = False
    for i, line in enumerate(lines):
        stripped = line.strip()

        # Check for Args: section start
        if stripped.lower() == "args:":
            in_args_section = True
            continue

        # Check for section end (Returns:, Raises:, etc.)
        if in_args_section and stripped.lower() in (
            "returns:",
            "raises:",
            "yields:",
            "examples:",
            "notes:",
            "attributes:",
        ):
            break

        # Parse parameter line in Args section
        if in_args_section and stripped:
            # Match patterns like "param_name (type): description" or "param_name: description"
            match = re.match(r"(\w+)\s*(?:\([^)]+\))?\s*:\s*(.+)", stripped)
            if match:
                param_name = match.group(1)
                desc = match.group(2).strip()
                descriptions[param_name] = desc

        # Also check for Sphinx-style :param lines
        if stripped.startswith(":param "):
            match = re.match(r":param\s+(\w+)\s*:\s*(.+)", stripped)
            if match:
                param_name = match.group(1)
                desc = match.group(2).strip()
                descriptions[param_name] = desc

    return descriptions


def _type_to_string(type_annotation) -> str:
    """Convert a type annotation to a string representation.

    Args:
        type_annotation: The type annotation to convert

    Returns:
        String representation of the type
    """
    if type_annotation is None or type_annotation is type(None):
        return "None"

    if hasattr(type_annotation, "__name__"):
        return type_annotation.__name__

    # Handle string annotations
    if isinstance(type_annotation, str):
        return type_annotation

    # Handle typing module types
    type_str = str(type_annotation)

    # Clean up typing module prefixes
    type_str = type_str.replace("typing.", "")

    return type_str
