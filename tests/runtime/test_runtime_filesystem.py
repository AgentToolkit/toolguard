"""Unit tests for ToolguardRuntime with filesystem-based loading."""

import pytest
from pathlib import Path
from typing import Any, Dict, Type

from toolguard.runtime import (
    load_toolguards,
    PolicyViolationException,
    IToolInvoker,
)


class MockToolInvoker(IToolInvoker):
    """Mock tool invoker for testing."""

    async def invoke(
        self, toolname: str, arguments: Dict[str, Any], return_type: Type
    ) -> Any:
        """Mock invoke that returns a simple result."""
        return {"result": "mocked"}


# Path to test data
TEST_DATA_DIR = Path(__file__).parent / "test_data" / "calculator"


@pytest.mark.asyncio
async def test_load_toolguards_from_filesystem():
    """Test basic loading of toolguards from filesystem."""
    runtime = load_toolguards(TEST_DATA_DIR)
    assert runtime is not None
    assert runtime._ctx_dir == TEST_DATA_DIR
    assert runtime._file_twins is None


@pytest.mark.asyncio
async def test_guard_toolcall_compliance():
    """Test guard_toolcall with compliant arguments."""
    mock_invoker = MockToolInvoker()

    with load_toolguards(TEST_DATA_DIR) as runtime:
        # Test add with positive numbers (should pass)
        await runtime.guard_toolcall("add_tool", {"a": 5, "b": 3}, mock_invoker)

        # Test divide with non-zero divisor (should pass)
        await runtime.guard_toolcall("divide_tool", {"a": 10, "b": 2}, mock_invoker)


@pytest.mark.asyncio
async def test_guard_toolcall_parallel_calls():
    """Test multiple parallel guard_toolcall invocations with compliance and violations."""
    import asyncio

    mock_invoker = MockToolInvoker()

    with load_toolguards(TEST_DATA_DIR) as runtime:
        # Create multiple parallel tasks - all compliant
        tasks_compliant = [
            runtime.guard_toolcall("add_tool", {"a": 5, "b": 3}, mock_invoker),
            runtime.guard_toolcall("add_tool", {"a": 10, "b": 20}, mock_invoker),
            runtime.guard_toolcall("divide_tool", {"a": 10, "b": 2}, mock_invoker),
            runtime.guard_toolcall("divide_tool", {"a": 20, "b": 5}, mock_invoker),
            runtime.guard_toolcall("add_tool", {"a": 1, "b": 1}, mock_invoker),
        ]

        # Execute all compliant tasks in parallel
        results = await asyncio.gather(*tasks_compliant)

        # All should complete without raising exceptions
        assert len(results) == 5

        # Test parallel calls with mix of compliance and violations
        tasks_mixed = [
            runtime.guard_toolcall(
                "add_tool", {"a": 5, "b": 3}, mock_invoker
            ),  # compliant
            runtime.guard_toolcall(
                "add_tool", {"a": -5, "b": 3}, mock_invoker
            ),  # violation
            runtime.guard_toolcall(
                "divide_tool", {"a": 10, "b": 2}, mock_invoker
            ),  # compliant
            runtime.guard_toolcall(
                "divide_tool", {"a": 10, "b": 0}, mock_invoker
            ),  # violation
            runtime.guard_toolcall(
                "add_tool", {"a": 100, "b": 200}, mock_invoker
            ),  # compliant
        ]

        # Use gather with return_exceptions=True to capture exceptions
        results_mixed = await asyncio.gather(*tasks_mixed, return_exceptions=True)

        # Check that we got the expected mix of results and exceptions
        assert len(results_mixed) == 5
        assert results_mixed[0] is None  # successful call
        assert isinstance(results_mixed[1], PolicyViolationException)  # negative number
        assert "positive numbers" in str(results_mixed[1]).lower()
        assert results_mixed[2] is None  # successful call
        assert isinstance(
            results_mixed[3], PolicyViolationException
        )  # division by zero
        assert "division by zero" in str(results_mixed[3]).lower()
        assert results_mixed[4] is None  # successful call


@pytest.mark.asyncio
async def test_guard_toolcall_violation_add():
    """Test guard_toolcall with policy violation for add tool."""
    mock_invoker = MockToolInvoker()

    with load_toolguards(TEST_DATA_DIR) as runtime:
        # Test add with negative number (should raise)
        with pytest.raises(PolicyViolationException) as exc_info:
            await runtime.guard_toolcall("add_tool", {"a": -5, "b": 3}, mock_invoker)

        with pytest.raises(PolicyViolationException) as exc_info:
            await runtime.guard_toolcall("add_tool", {"a": 5, "b": -3}, mock_invoker)

        with pytest.raises(PolicyViolationException) as exc_info:
            await runtime.guard_toolcall("add_tool", {"a": -5, "b": -3}, mock_invoker)

        assert "positive numbers" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_guard_toolcall_violation_divide():
    """Test guard_toolcall with policy violation for divide tool."""
    mock_invoker = MockToolInvoker()

    with load_toolguards(TEST_DATA_DIR) as runtime:
        # Test divide by zero (should raise)
        with pytest.raises(PolicyViolationException) as exc_info:
            await runtime.guard_toolcall("divide_tool", {"a": 10, "b": 0}, mock_invoker)

        assert "division by zero" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_guard_toolcall_no_guard():
    """Test guard_toolcall with a tool that has no guard."""
    mock_invoker = MockToolInvoker()

    with load_toolguards(TEST_DATA_DIR) as runtime:
        # Call a tool that doesn't exist (should not raise)
        await runtime.guard_toolcall("nonexistent_tool", {"a": 5, "b": 3}, mock_invoker)


@pytest.mark.asyncio
async def test_multiple_violations():
    """Test multiple policy violations in sequence."""
    mock_invoker = MockToolInvoker()

    with load_toolguards(TEST_DATA_DIR) as runtime:
        # First violation
        with pytest.raises(PolicyViolationException):
            await runtime.guard_toolcall("add_tool", {"a": -1, "b": 5}, mock_invoker)

        # Second violation
        with pytest.raises(PolicyViolationException):
            await runtime.guard_toolcall("divide_tool", {"a": 5, "b": 0}, mock_invoker)

        # Compliant call after violations
        await runtime.guard_toolcall("add_tool", {"a": 5, "b": 3}, mock_invoker)


@pytest.mark.asyncio
async def test_context_manager_restores_path():
    """Test that context manager restores sys.path after exit."""
    import sys

    original_path = list(sys.path)

    with load_toolguards(TEST_DATA_DIR) as runtime:
        assert runtime is not None
        # Path should be modified
        assert str(TEST_DATA_DIR.absolute()) in sys.path

    # Path should be restored
    assert sys.path == original_path


@pytest.mark.asyncio
async def test_filesystem_mode_behavior_matches_memory():
    """Test that both modes behave identically for the same inputs."""
    from toolguard.runtime import load_toolguards_from_memory
    from toolguard.runtime.data_types import ToolGuardsCodeGenerationResult

    mock_invoker = MockToolInvoker()

    # Test with filesystem mode
    with load_toolguards(TEST_DATA_DIR) as fs_runtime:
        # Should pass
        await fs_runtime.guard_toolcall("add_tool", {"a": 5, "b": 3}, mock_invoker)

        # Should fail
        with pytest.raises(PolicyViolationException):
            await fs_runtime.guard_toolcall("add_tool", {"a": -5, "b": 3}, mock_invoker)

    # Test with memory mode
    result = ToolGuardsCodeGenerationResult.load(TEST_DATA_DIR)
    with load_toolguards_from_memory(result) as mem_runtime:
        # Should pass
        await mem_runtime.guard_toolcall("add_tool", {"a": 5, "b": 3}, mock_invoker)

        # Should fail
        with pytest.raises(PolicyViolationException):
            await mem_runtime.guard_toolcall(
                "add_tool", {"a": -5, "b": 3}, mock_invoker
            )


# Made with Bob
