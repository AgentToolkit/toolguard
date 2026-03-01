from abc import ABC, abstractmethod
from test_api_types import CalculatorArgs


class ITestApi(ABC):
    @abstractmethod
    async def add(self, args: CalculatorArgs) -> int:
        pass

    @abstractmethod
    async def divide(self, args: CalculatorArgs) -> float:
        pass


# Made with Bob
