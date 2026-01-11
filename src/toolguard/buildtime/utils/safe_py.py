from typing import List
from smolagents.local_python_executor import LocalPythonExecutor


def run_safe_python(code: str, libs: List[str] = []):
    exec = LocalPythonExecutor(
        additional_authorized_imports=libs,
        max_print_outputs_length=None,
        additional_functions=None,
    )
    out = exec(code)
    return out
