"""Accepting every tool-description shape v2 supports.

v1's ``_tools_to_tool_infos`` documents a ``list[ToolInfo]`` branch but
raises on it. v2 needs that branch, because a caller holding MCP tool
definitions already has exactly that.
"""

from pathlib import Path

import pytest

from toolguard.buildtime.gen_spec.data_types import ToolInfo, ToolInfoParam
from toolguard.buildtime.gen_spec_v2.tools_input import to_tool_infos
from toolguard.buildtime.utils.open_api import OpenAPI

OAS_PATH = Path("tests/examples/appointments/appointments_oas.json")


def _tool_info(name: str) -> ToolInfo:
    return ToolInfo(
        name=name,
        summary="",
        description=f"{name} does a thing",
        parameters={
            "user_id": ToolInfoParam(type="int", description=None, required=True)
        },
        signature="",
    )


def test_tool_info_list_passes_through():
    infos = [_tool_info("get_employee"), _tool_info("set_passport")]

    assert [t.name for t in to_tool_infos(infos)] == ["get_employee", "set_passport"]


def test_openapi_dict_is_converted():
    oas = OpenAPI.load_from(OAS_PATH)

    names = [t.name for t in to_tool_infos(oas.model_dump(by_alias=True))]

    assert "add_payment_method" in names


def test_callables_are_converted():
    def transfer(user_id: int, amount: float) -> bool:
        """Transfer money."""
        return True

    infos = to_tool_infos([transfer])

    assert infos[0].name == "transfer"
    assert set(infos[0].parameters) == {"user_id", "amount"}


def test_unsupported_input_is_rejected():
    # Deliberately off-type: the guard exists for callers without type checking.
    with pytest.raises(NotImplementedError):
        to_tool_infos([object()])  # type: ignore[list-item]


def test_empty_list_is_rejected():
    with pytest.raises(ValueError):
        to_tool_infos([])
