from pydantic import BaseModel


class CalculatorArgs(BaseModel):
    a: int
    b: int


# Made with Bob
