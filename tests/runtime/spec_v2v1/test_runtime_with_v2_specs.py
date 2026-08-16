"""The runtime, driven by specs that came from v2 with `skip` computed in memory.

The existing runtime tests build their `ToolGuardSpec`s by hand. These mirror
them using the v2 models converted through `v1_compat`, reusing the same
calculator guard code and domain from `tests/runtime/test_data`, to establish
that a v2-sourced spec is indistinguishable to the runtime.

Nothing here asserts anything about generation quality, and no v1 test is
touched.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Type

import pytest

from toolguard.buildtime.gen_spec_v2.data_types import (
    PolicyItemV2,
    Requires,
    ToolGuardSpecV2,
)
from toolguard.buildtime.gen_spec_v2.v1_compat import to_v1_spec
from toolguard.runtime import (
    IToolInvoker,
    PolicyViolationException,
    load_toolguards_from_memory,
)
from toolguard.runtime.data_types import (
    ToolGuardCodeResult,
    ToolGuardsCodeGenerationResult,
)

TEST_DATA_DIR = Path(__file__).parents[1] / "test_data" / "calculator"


class MockToolInvoker(IToolInvoker):
    async def invoke(
        self, toolname: str, arguments: Dict[str, Any], return_type: Type
    ) -> Any:
        return {"result": "mocked"}


def v2_item(item_id: str, name: str, description: str, **kwargs) -> PolicyItemV2:
    return PolicyItemV2(
        id=item_id,
        name=name,
        description=description,
        compliance_examples=["a compliant call"],
        violation_examples=["a violating call"],
        references=["The calculator must not allow division by zero."],
        trigger=kwargs.pop("trigger", "pre_tool"),
        requires=kwargs.pop("requires", Requires()),
        **kwargs,
    )


def v2_add_spec() -> ToolGuardSpecV2:
    return ToolGuardSpecV2(
        tool_name="add_tool",
        source_doc="inputs/policy_doc.md",
        policy_items=[
            v2_item(
                "add_tool.positive_numbers",
                "positive_numbers",
                "Only positive numbers are allowed",
            )
        ],
    )


def v2_divide_spec() -> ToolGuardSpecV2:
    return ToolGuardSpecV2(
        tool_name="divide_tool",
        source_doc="inputs/policy_doc.md",
        policy_items=[
            v2_item(
                "divide_tool.no_division_by_zero",
                "no_division_by_zero",
                "Division by zero is not allowed",
            )
        ],
    )


def result_with_specs(specs: List[ToolGuardSpecV2]) -> ToolGuardsCodeGenerationResult:
    """The committed calculator result, with its specs replaced by v2-sourced ones.

    Everything else -- domain, guard code, file twins -- is the same artifact the
    v1 runtime tests load, so the only thing under test is the spec.
    """
    on_disk = ToolGuardsCodeGenerationResult.model_validate(
        json.loads((TEST_DATA_DIR / "result.json").read_text(encoding="utf-8"))
    )
    for spec in specs:
        tool = on_disk.tools[spec.tool_name]
        on_disk.tools[spec.tool_name] = ToolGuardCodeResult(
            tool=to_v1_spec(spec),
            guard_fn_name=tool.guard_fn_name,
            guard_file=tool.guard_file,
            item_guard_files=tool.item_guard_files,
            test_files=tool.test_files,
        )
    return on_disk


@pytest.fixture
def v2_sourced_result() -> ToolGuardsCodeGenerationResult:
    return result_with_specs([v2_add_spec(), v2_divide_spec()])


async def test_the_runtime_loads_a_v2_sourced_result(v2_sourced_result):
    with load_toolguards_from_memory(v2_sourced_result) as runtime:
        assert runtime is not None
        assert set(v2_sourced_result.tools) == {"add_tool", "divide_tool"}


async def test_compliant_calls_pass(v2_sourced_result):
    invoker = MockToolInvoker()
    with load_toolguards_from_memory(v2_sourced_result) as runtime:
        await runtime.guard_toolcall("add_tool", {"a": 5, "b": 3}, invoker)
        await runtime.guard_toolcall("divide_tool", {"a": 10, "b": 2}, invoker)


async def test_a_violating_add_still_raises(v2_sourced_result):
    invoker = MockToolInvoker()
    with load_toolguards_from_memory(v2_sourced_result) as runtime:
        with pytest.raises(PolicyViolationException) as exc_info:
            await runtime.guard_toolcall("add_tool", {"a": -5, "b": 3}, invoker)
        assert "positive numbers" in str(exc_info.value).lower()


async def test_a_violating_divide_still_raises(v2_sourced_result):
    invoker = MockToolInvoker()
    with load_toolguards_from_memory(v2_sourced_result) as runtime:
        with pytest.raises(PolicyViolationException) as exc_info:
            await runtime.guard_toolcall("divide_tool", {"a": 10, "b": 0}, invoker)
        assert "division by zero" in str(exc_info.value).lower()


async def test_an_unguarded_tool_is_left_alone(v2_sourced_result):
    invoker = MockToolInvoker()
    with load_toolguards_from_memory(v2_sourced_result) as runtime:
        await runtime.guard_toolcall("nonexistent_tool", {"a": 5, "b": 3}, invoker)


async def test_the_v1_view_keeps_what_the_runtime_carries(v2_sourced_result):
    spec = v2_sourced_result.tools["divide_tool"].tool
    item = spec.policy_items[0]
    assert spec.tool_name == "divide_tool"
    assert item.name == "no_division_by_zero"
    assert item.description == "Division by zero is not allowed"
    assert item.skip is False
    assert item.debug["v2"]["id"] == "divide_tool.no_division_by_zero"


async def test_a_skipped_rule_still_loads_and_guards(v2_sourced_result):
    """A rule v1 cannot codegen is marked skip, but the guard code already exists.

    The runtime executes generated code, not the spec, so a skipped item changes
    nothing at guard time -- it only tells `gen_py` not to generate for it.
    """
    subject_bound = v2_divide_spec()
    subject_bound.policy_items[0].requires = Requires(system_vars=["user_id"])
    result = result_with_specs([v2_add_spec(), subject_bound])

    assert result.tools["divide_tool"].tool.policy_items[0].skip is True

    invoker = MockToolInvoker()
    with load_toolguards_from_memory(result) as runtime:
        await runtime.guard_toolcall("divide_tool", {"a": 10, "b": 2}, invoker)
        with pytest.raises(PolicyViolationException):
            await runtime.guard_toolcall("divide_tool", {"a": 10, "b": 0}, invoker)
