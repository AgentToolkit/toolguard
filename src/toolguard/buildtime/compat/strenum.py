import sys
from enum import Enum

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    # Python ≤ 3.10 fallback
    class StrEnum(str, Enum):
        """
        Backport of enum.StrEnum for Python < 3.11.

        Behaves like a str and an Enum.
        """

        def __str__(self) -> str:
            return str(self.value)


__all__ = ["StrEnum"]
