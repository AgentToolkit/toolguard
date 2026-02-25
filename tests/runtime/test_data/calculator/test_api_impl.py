from test_api import ITestApi
from test_api_types import CalculatorArgs


class TestApiImpl(ITestApi):
    def __init__(self, delegate):
        self.delegate = delegate

    async def add(self, args: CalculatorArgs) -> int:
        return await self.delegate.invoke("add_tool", {"a": args.a, "b": args.b}, int)

    async def divide(self, args: CalculatorArgs) -> float:
        return await self.delegate.invoke(
            "divide_tool", {"a": args.a, "b": args.b}, float
        )


# Made with Bob
