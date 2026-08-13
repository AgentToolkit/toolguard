"""Failure reporting shared by both spec generators.

A build that quietly produces 31 specs for 33 tools ships two tools unguarded,
and the shortfall is indistinguishable from a smaller request. Both generators
therefore finish every healthy tool, write it, and then raise one error that
names what was lost -- so a caller learns which tools failed without counting
files in the output directory.
"""

from typing import Any, List, Sequence

from pydantic import BaseModel


class ToolFailure(BaseModel):
    """One tool's generation failure."""

    tool_name: str
    error: str


class SpecGenerationError(Exception):
    """Some tools failed. Carries both sides of the outcome.

    ``specs`` are the specs that generated cleanly and were written to disk --
    v1's ``ToolGuardSpec`` or v2's ``SpecV2``, depending on which generator
    raised. ``failures`` name the tools that did not.
    """

    def __init__(self, failures: Sequence[ToolFailure], specs: Sequence[Any]):
        self.failures: List[ToolFailure] = list(failures)
        self.specs: List[Any] = list(specs)
        detail = "; ".join(f"{f.tool_name}: {f.error}" for f in self.failures)
        super().__init__(
            f"Spec generation failed for {len(self.failures)} tool(s) "
            f"({len(self.specs)} succeeded): {detail}"
        )
