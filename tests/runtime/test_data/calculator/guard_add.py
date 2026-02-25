from test_api_types import CalculatorArgs
from toolguard.runtime.data_types import PolicyViolationException


async def guard_add_tool(args: CalculatorArgs):
    """Guard for add tool - ensures positive numbers only."""
    if args.a < 0 or args.b < 0:
        raise PolicyViolationException("Only positive numbers are allowed")


# Made with Bob
