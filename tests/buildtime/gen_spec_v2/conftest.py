"""A scripted LLM for the stage and pipeline tests, plus the corpus paths.

Responses are keyed by the ``[STAGE:x]`` marker every v2 user prompt carries,
so a test declares what each stage answers without caring about call order or
concurrency.
"""

import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Union

import pytest

from toolguard.buildtime.gen_spec.data_types import ToolInfo, ToolInfoParam
from toolguard.buildtime.gen_spec_v2.context import GenContext
from toolguard.buildtime.llm import I_TG_LLM

CORPUS_DIR = Path("tests/examples/employee_mini")
"""A committed six-spec slice of the employee ground truth.

Real generator output, so the format, grounding and identifier gates test what
a model actually produces rather than what a synthetic fixture remembers to
include. The full 28-spec example and its benchmarks live in the
evaluate-toolguard project; see this directory's README for what was kept and
why.
"""

CORPUS_SPECS_DIR = CORPUS_DIR / "specs"
CORPUS_GUIDANCE = CORPUS_DIR / "guidance.txt"
CORPUS_SYSTEM_VARS = CORPUS_DIR / "system_vars.json"

STAGE_MARKER = re.compile(r"\[STAGE:(\w+)\]")

Response = Union[Dict[str, Any], Callable[[str], Dict[str, Any]], Exception]


class FakeLLM(I_TG_LLM):
    """Returns a canned response per stage, and records every call."""

    def __init__(self, responses: Dict[str, Response]):
        self.responses = responses
        self.calls: List[Dict[str, str]] = []

    async def chat_json(self, messages: List[Dict]) -> Dict:
        user_content = messages[-1]["content"]
        match = STAGE_MARKER.search(user_content)
        stage = match.group(1) if match else "unknown"
        self.calls.append({"stage": stage, "content": user_content})

        response = self.responses.get(stage, {})
        if isinstance(response, Exception):
            raise response
        if callable(response):
            return response(user_content)
        return response

    async def generate(self, messages: List[Dict]) -> str:
        raise NotImplementedError

    def calls_for(self, stage: str) -> List[Dict[str, str]]:
        return [call for call in self.calls if call["stage"] == stage]

    def count(self, stage: str) -> int:
        return len(self.calls_for(stage))


POLICY = """# Employee Policy

- **HR** may view and edit all employees' data.
- An employee's `salary` may be updated only by **HR** or by that employee's **direct manager**.
- When an employee's **salary** is set or updated, it must be a positive amount (greater than zero).
"""

SYSTEM_VARS = {
    "user_id": 1,
    "department": ["Corporate Leadership", "Engineering", "HR", "Finance"],
    "organization": ["IBM Corporation", "Red Hat", "Kyndryl"],
}


def make_tool(name: str, description: str = "does a thing") -> ToolInfo:
    return ToolInfo(
        name=name,
        summary="",
        description=description,
        parameters={
            "user_id": ToolInfoParam(type="int", description="who", required=True),
            "salary": ToolInfoParam(type="float", description="pay", required=False),
        },
        signature=f"{name}(user_id: int, salary: float) -> dict",
    )


@pytest.fixture
def tool() -> ToolInfo:
    return make_tool("update_employee", "Update an employee")


@pytest.fixture
def other_tool() -> ToolInfo:
    return make_tool("get_employee", "Read an employee")


@pytest.fixture
def ctx(tool, other_tool) -> GenContext:
    return GenContext.build(POLICY, [tool, other_tool], SYSTEM_VARS)
