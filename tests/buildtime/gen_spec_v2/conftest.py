"""Shared fixtures: a scripted fake LLM and the in-repo mini benchmark."""

import importlib.util
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest
from jsonschema import Draft202012Validator

from toolguard.buildtime.gen_spec.data_types import ToolInfo
from toolguard.buildtime.gen_spec.fn_to_toolinfo import function_to_toolInfo
from toolguard.buildtime.llm import I_TG_LLM

MINI_INPUTS = Path(__file__).parents[2] / "examples" / "employee_mini" / "inputs"
SCHEMA_PATH = Path(__file__).parent / "step1.schema.json"
_STAGE = re.compile(r"\[STAGE:(\w+)\]")


class FakeLLM(I_TG_LLM):
    """Answers by pipeline stage, recording every call.

    ``by_stage`` maps a stage name (the ``[STAGE:x]`` marker every prompt
    carries) to a response: a dict, a callable taking the user prompt and
    returning a dict, or an exception to raise.
    """

    def __init__(self, by_stage: Dict[str, Any]):
        self.by_stage = by_stage
        self.calls: List[Tuple[str, str]] = []

    @property
    def stages(self) -> List[str]:
        return [stage for stage, _ in self.calls]

    def calls_for(self, stage: str) -> List[str]:
        return [prompt for name, prompt in self.calls if name == stage]

    async def chat_json(self, messages: List[Dict]) -> Dict:
        prompt = messages[-1]["content"]
        match = _STAGE.search(prompt)
        assert match, f"prompt carries no [STAGE:] marker: {prompt[:120]}"
        stage = match.group(1)
        self.calls.append((stage, prompt))
        response = self.by_stage.get(stage)
        if response is None:
            raise AssertionError(
                f"FakeLLM has no scripted response for stage {stage!r}"
            )
        if callable(response):
            response = response(prompt)
        if isinstance(response, BaseException):
            raise response
        return response

    async def generate(self, messages: List[Dict]) -> str:
        raise NotImplementedError("gen_spec_v2 only uses chat_json")


@pytest.fixture(scope="session")
def mini_policy() -> str:
    return (MINI_INPUTS / "policy_doc.md").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def mini_sys_var() -> dict:
    return json.loads((MINI_INPUTS / "system_vars.json").read_text(encoding="utf-8"))


def load_mini_tools_module(alias: str = "employee_mini_tools"):
    """Import the fixture's tool functions by path -- they are not a package.

    ``alias`` keeps separate test modules from sharing one entry in
    ``sys.modules`` when they load the file for different purposes.
    """
    spec = importlib.util.spec_from_file_location(
        alias, MINI_INPUTS / "tool_functions.py"
    )
    assert spec is not None and spec.loader is not None, "fixture module not found"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def mini_tools() -> List[ToolInfo]:
    module = load_mini_tools_module()
    names = [
        "get_bank_account",
        "get_direct_reports",
        "update_employee",
        "update_passport",
        "create_time_off_request",
    ]
    return [function_to_toolInfo(getattr(module, name)) for name in names]


@pytest.fixture(scope="session")
def schema_validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
