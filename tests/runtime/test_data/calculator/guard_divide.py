from test_api_types import CalculatorArgs
from toolguard.runtime.data_types import PolicyViolationException


async def guard_divide_tool(args: CalculatorArgs):
    """Guard for divide tool - prevents division by zero."""
    if args.b == 0:
        raise PolicyViolationException("Division by zero is not allowed")


# Made with Bob
