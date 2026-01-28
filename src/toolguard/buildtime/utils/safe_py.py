import asyncio
from concurrent.futures import ProcessPoolExecutor
from typing import List

from smolagents.local_python_executor import LocalPythonExecutor


def _execute_in_process(code: str, libs: List[str]) -> str:
    """Execute code in LocalPythonExecutor. This function runs in a separate process."""
    executor = LocalPythonExecutor(
        additional_authorized_imports=libs,
        max_print_outputs_length=None,
        additional_functions=None,
    )
    out = executor(code)
    return out


async def run_safe_python(code: str, libs: List[str] = []) -> str:
    """Run Python code safely in a separate process.

    This executes code in an isolated process using LocalPythonExecutor,
    which provides a safe execution environment with controlled imports.
    Running in a separate process avoids module caching issues when code
    is being modified during runtime.

    Args:
        code: The Python code to execute.
        libs: List of additional authorized import libraries (default: []).

    Returns:
        The output from the code execution.
    """
    loop = asyncio.get_event_loop()
    with ProcessPoolExecutor(max_workers=1) as executor:
        result = await loop.run_in_executor(executor, _execute_in_process, code, libs)
    return result
