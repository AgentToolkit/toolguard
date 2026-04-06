"""Unit tests for ToolguardRuntime with in-memory FileTwin objects."""

import pytest
from pathlib import Path
from typing import Any, Dict, Type

from toolguard.runtime import (
    load_toolguards_from_memory,
    PolicyViolationException,
    IToolInvoker,
)
from toolguard.runtime.data_types import (
    FileTwin,
    ToolGuardsCodeGenerationResult,
    ToolGuardCodeResult,
    ToolGuardSpec,
    ToolGuardSpecItem,
    RuntimeDomain,
)


class MockToolInvoker(IToolInvoker):
    """Mock tool invoker for testing."""

    async def invoke(
        self, toolname: str, arguments: Dict[str, Any], return_type: Type
    ) -> Any:
        """Mock invoke that returns a simple result."""
        return {"result": "mocked"}


@pytest.fixture
def sample_api_types():
    """Create sample API types file."""
    return FileTwin(
        file_name=Path("test_api_types.py"),
        content="""
from pydantic import BaseModel

class CalculatorArgs(BaseModel):
    a: int
    b: int
""",
    )


@pytest.fixture
def sample_api_interface():
    """Create sample API interface file."""
    return FileTwin(
        file_name=Path("test_api.py"),
        content="""
from abc import ABC, abstractmethod
from typing import Any, Dict, Type
from test_api_types import CalculatorArgs

class ITestApi(ABC):
    @abstractmethod
    async def add(self, args: CalculatorArgs) -> int:
        pass

    @abstractmethod
    async def divide(self, args: CalculatorArgs) -> float:
        pass
""",
    )


@pytest.fixture
def sample_api_impl():
    """Create sample API implementation file."""
    return FileTwin(
        file_name=Path("test_api_impl.py"),
        content="""
from typing import Any, Dict, Type
from test_api import ITestApi
from test_api_types import CalculatorArgs

class TestApiImpl(ITestApi):
    def __init__(self, delegate):
        self.delegate = delegate

    async def add(self, args: CalculatorArgs) -> int:
        return await self.delegate.invoke("add_tool", {"a": args.a, "b": args.b}, int)

    async def divide(self, args: CalculatorArgs) -> float:
        return await self.delegate.invoke("divide_tool", {"a": args.a, "b": args.b}, float)
""",
    )


@pytest.fixture
def sample_guard_add():
    """Create sample guard for add tool."""
    return FileTwin(
        file_name=Path("guard_add.py"),
        content="""
from test_api_types import CalculatorArgs
from toolguard.runtime.data_types import PolicyViolationException

async def guard_add_tool(args: CalculatorArgs):
    '''Guard for add tool - ensures positive numbers only.'''
    if args.a < 0 or args.b < 0:
        raise PolicyViolationException("Only positive numbers are allowed")
""",
    )


@pytest.fixture
def sample_guard_divide():
    """Create sample guard for divide tool."""
    return FileTwin(
        file_name=Path("guard_divide.py"),
        content="""
from test_api_types import CalculatorArgs
from toolguard.runtime.data_types import PolicyViolationException

async def guard_divide_tool(args: CalculatorArgs):
    '''Guard for divide tool - prevents division by zero.'''
    if args.b == 0:
        raise PolicyViolationException("Division by zero is not allowed")
""",
    )


@pytest.fixture
def sample_result(
    sample_api_types,
    sample_api_interface,
    sample_api_impl,
    sample_guard_add,
    sample_guard_divide,
):
    """Create a sample ToolGuardsCodeGenerationResult."""
    domain = RuntimeDomain(
        app_name="TestCalculator",
        app_types=sample_api_types,
        app_api_class_name="ITestApi",
        app_api=sample_api_interface,
        app_api_size=2,
        app_api_impl_class_name="TestApiImpl",
        app_api_impl=sample_api_impl,
    )

    add_spec = ToolGuardSpec(
        tool_name="add_tool",
        policy_items=[
            ToolGuardSpecItem(
                name="positive_numbers",
                description="Only positive numbers are allowed",
                references=[],
                compliance_examples=["add(5, 3)", "add(10, 20)"],
                violation_examples=["add(-5, 3)", "add(5, -3)"],
            )
        ],
    )

    divide_spec = ToolGuardSpec(
        tool_name="divide_tool",
        policy_items=[
            ToolGuardSpecItem(
                name="no_division_by_zero",
                description="Division by zero is not allowed",
                references=[],
                compliance_examples=["divide(10, 2)", "divide(20, 5)"],
                violation_examples=["divide(10, 0)"],
            )
        ],
    )

    return ToolGuardsCodeGenerationResult(
        out_dir=Path("/tmp/test"),
        domain=domain,
        tools={
            "add_tool": ToolGuardCodeResult(
                tool=add_spec,
                guard_fn_name="guard_add_tool",
                guard_file=sample_guard_add,
                item_guard_files=[],
                test_files=[],
            ),
            "divide_tool": ToolGuardCodeResult(
                tool=divide_spec,
                guard_fn_name="guard_divide_tool",
                guard_file=sample_guard_divide,
                item_guard_files=[],
                test_files=[],
            ),
        },
    )


@pytest.mark.asyncio
async def test_load_toolguards_from_memory_basic(
    sample_result,
    sample_api_types,
    sample_api_interface,
    sample_api_impl,
    sample_guard_add,
    sample_guard_divide,
):
    """Test basic loading of toolguards from memory."""
    runtime = load_toolguards_from_memory(sample_result)
    assert runtime is not None
    assert runtime._file_twins is not None
    assert len(runtime._file_twins) > 0
    assert runtime._ctx_dir is None


@pytest.mark.asyncio
async def test_guard_toolcall_compliance(
    sample_result,
    sample_api_types,
    sample_api_interface,
    sample_api_impl,
    sample_guard_add,
    sample_guard_divide,
):
    """Test guard_toolcall with compliant arguments."""
    mock_invoker = MockToolInvoker()

    with load_toolguards_from_memory(sample_result) as runtime:
        # Test add with positive numbers (should pass)
        await runtime.guard_toolcall("add_tool", {"a": 5, "b": 3}, mock_invoker)

        # Test divide with non-zero divisor (should pass)
        await runtime.guard_toolcall("divide_tool", {"a": 10, "b": 2}, mock_invoker)


@pytest.mark.asyncio
async def test_guard_toolcall_parallel_calls(
    sample_result,
    sample_api_types,
    sample_api_interface,
    sample_api_impl,
    sample_guard_add,
    sample_guard_divide,
):
    """Test multiple parallel guard_toolcall invocations."""
    import asyncio

    mock_invoker = MockToolInvoker()

    with load_toolguards_from_memory(sample_result) as runtime:
        # Create multiple parallel tasks
        tasks = [
            runtime.guard_toolcall("add_tool", {"a": 5, "b": 3}, mock_invoker),
            runtime.guard_toolcall("add_tool", {"a": 10, "b": 20}, mock_invoker),
            runtime.guard_toolcall("divide_tool", {"a": 10, "b": 2}, mock_invoker),
            runtime.guard_toolcall("divide_tool", {"a": 20, "b": 5}, mock_invoker),
            runtime.guard_toolcall("add_tool", {"a": 1, "b": 1}, mock_invoker),
        ]

        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks)

        # All should complete without raising exceptions
        assert len(results) == 5

        # Test parallel calls with some violations
        tasks_with_violations = [
            runtime.guard_toolcall("add_tool", {"a": 5, "b": 3}, mock_invoker),
            runtime.guard_toolcall(
                "add_tool", {"a": -5, "b": 3}, mock_invoker
            ),  # violation
            runtime.guard_toolcall("divide_tool", {"a": 10, "b": 2}, mock_invoker),
            runtime.guard_toolcall(
                "divide_tool", {"a": 10, "b": 0}, mock_invoker
            ),  # violation
        ]

        # Use gather with return_exceptions=True to capture exceptions
        results_with_exceptions = await asyncio.gather(
            *tasks_with_violations, return_exceptions=True
        )

        # Check that we got the expected mix of results and exceptions
        assert len(results_with_exceptions) == 4
        assert results_with_exceptions[0] is None  # successful call
        assert isinstance(
            results_with_exceptions[1], PolicyViolationException
        )  # negative number
        assert results_with_exceptions[2] is None  # successful call
        assert isinstance(
            results_with_exceptions[3], PolicyViolationException
        )  # division by zero


@pytest.mark.asyncio
async def test_guard_toolcall_violation_add(
    sample_result,
    sample_api_types,
    sample_api_interface,
    sample_api_impl,
    sample_guard_add,
    sample_guard_divide,
):
    """Test guard_toolcall with policy violation for add tool."""
    mock_invoker = MockToolInvoker()

    with load_toolguards_from_memory(sample_result) as runtime:
        # Test add with negative number (should raise)
        with pytest.raises(PolicyViolationException) as exc_info:
            await runtime.guard_toolcall("add_tool", {"a": -5, "b": 3}, mock_invoker)
        assert "positive numbers" in str(exc_info.value).lower()

        with pytest.raises(PolicyViolationException) as exc_info:
            await runtime.guard_toolcall("add_tool", {"a": 5, "b": -3}, mock_invoker)
        assert "positive numbers" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_guard_toolcall_violation_divide(
    sample_result,
    sample_api_types,
    sample_api_interface,
    sample_api_impl,
    sample_guard_add,
    sample_guard_divide,
):
    """Test guard_toolcall with policy violation for divide tool."""
    mock_invoker = MockToolInvoker()

    with load_toolguards_from_memory(sample_result) as runtime:
        # Test divide by zero (should raise)
        with pytest.raises(PolicyViolationException) as exc_info:
            await runtime.guard_toolcall("divide_tool", {"a": 10, "b": 0}, mock_invoker)

        assert "division by zero" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_guard_toolcall_no_guard(
    sample_result,
    sample_api_types,
    sample_api_interface,
    sample_api_impl,
    sample_guard_add,
    sample_guard_divide,
):
    """Test guard_toolcall with a tool that has no guard."""
    mock_invoker = MockToolInvoker()

    with load_toolguards_from_memory(sample_result) as runtime:
        # Call a tool that doesn't exist (should not raise)
        await runtime.guard_toolcall("nonexistent_tool", {"a": 5, "b": 3}, mock_invoker)


def test_runtime_init_validation():
    """Test that runtime initialization validates arguments."""
    from toolguard.runtime.runtime import ToolguardRuntime
    from toolguard.runtime.data_types import ToolGuardsCodeGenerationResult

    # Create a minimal result object
    result = ToolGuardsCodeGenerationResult(
        out_dir=Path("/tmp/test"),
        domain=RuntimeDomain(
            app_name="Test",
            app_types=FileTwin(file_name=Path("types.py"), content=""),
            app_api_class_name="IApi",
            app_api=FileTwin(file_name=Path("api.py"), content=""),
            app_api_size=0,
            app_api_impl_class_name="ApiImpl",
            app_api_impl=FileTwin(file_name=Path("api_impl.py"), content=""),
        ),
        tools={},
    )

    # Should raise if neither ctx_dir nor file_twins provided
    with pytest.raises(
        ValueError, match="Either ctx_dir or file_twins must be provided"
    ):
        ToolguardRuntime(result)

    # Should raise if both ctx_dir and file_twins provided
    with pytest.raises(
        ValueError, match="Only one of ctx_dir or file_twins should be provided"
    ):
        ToolguardRuntime(result, ctx_dir=Path("/tmp"), file_twins=[])


# Made with Bob
