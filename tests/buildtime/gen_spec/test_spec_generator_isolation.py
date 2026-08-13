"""One tool's failure must not take the rest of the run with it.

v1 fanned out over the tools with a bare ``asyncio.gather``, so the first
exception discarded every other tool's finished spec -- 33 tools lost to one
unparseable response.
"""

from pathlib import Path
from typing import Dict, List

import pytest

from toolguard.buildtime.gen_spec.spec_generator import (
    PolicySpecOptions,
    SpecGenerationError,
    extract_toolguard_specs,
)
from toolguard.buildtime.llm import I_TG_LLM

POLICY = "Only HR may edit an employee's data."


def update_employee(user_id: int, salary: float) -> dict:
    """Update an employee."""
    return {}


def get_employee(user_id: int) -> dict:
    """Read an employee."""
    return {}


TOOLS = [update_employee, get_employee]

SPEC_RESPONSE = {
    "policy_items": [
        {
            "name": "HR only",
            "description": "Only HR may edit.",
            "references": ["Only HR may edit an employee's data."],
        }
    ]
}


class BoomForOneTool(I_TG_LLM):
    """Answers every prompt, except those naming the doomed tool."""

    def __init__(self, doomed: str):
        self.doomed = doomed
        self.seen: List[str] = []

    async def chat_json(self, messages: List[Dict]) -> Dict:
        content = messages[-1]["content"]
        self.seen.append(content)
        # Key on the target section, not the catalog that every prompt carries,
        # so only the doomed tool's pipeline fails.
        _, _, target = content.partition("Target Tool:")
        if f'"name": "{self.doomed}"' in target:
            raise RuntimeError("could not obtain valid JSON")
        return SPEC_RESPONSE

    async def generate(self, messages: List[Dict]) -> str:
        raise NotImplementedError


def _options() -> PolicySpecOptions:
    # Only the first step and no examples, so the test pins fan-out behaviour
    # rather than the content of the later passes.
    return PolicySpecOptions(spec_steps={"CREATE_POLICIES"}, example_number=0)


async def test_a_failing_tool_does_not_discard_the_others(tmp_path: Path):
    llm = BoomForOneTool("get_employee")

    with pytest.raises(SpecGenerationError) as exc_info:
        await extract_toolguard_specs(POLICY, TOOLS, tmp_path, llm, options=_options())

    assert [s.tool_name for s in exc_info.value.specs] == ["update_employee"]
    assert (tmp_path / "update_employee.json").exists()


async def test_the_error_names_the_failed_tool(tmp_path: Path):
    llm = BoomForOneTool("get_employee")

    with pytest.raises(SpecGenerationError) as exc_info:
        await extract_toolguard_specs(POLICY, TOOLS, tmp_path, llm, options=_options())

    assert [f.tool_name for f in exc_info.value.failures] == ["get_employee"]
    assert "get_employee" in str(exc_info.value)


async def test_a_clean_run_still_returns_every_spec(tmp_path: Path):
    llm = BoomForOneTool("nothing_matches_this")

    specs = await extract_toolguard_specs(
        POLICY, TOOLS, tmp_path, llm, options=_options()
    )

    assert sorted(s.tool_name for s in specs) == ["get_employee", "update_employee"]
