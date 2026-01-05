from ..common.str import to_snake_case
from ..data_types import ToolGuardSpec, ToolGuardSpecItem


RUNTIME_PACKAGE_NAME = "rt_toolguard"
RUNTIME_INIT_PY = "__init__.py"
RUNTIME_TYPES_PY = "data_types.py"
RUNTIME_APP_TYPES_PY = "domain_types.py"


def guard_fn_name(tool_policy: ToolGuardSpec) -> str:
    return to_snake_case(f"guard_{tool_policy.tool_name}")


def guard_fn_module_name(tool_policy: ToolGuardSpec) -> str:
    return to_snake_case(f"guard_{tool_policy.tool_name}")


def guard_item_fn_name(tool_item: ToolGuardSpecItem) -> str:
    return to_snake_case(f"guard_{tool_item.name}")


def guard_item_fn_module_name(tool_item: ToolGuardSpecItem) -> str:
    return to_snake_case(f"guard_{tool_item.name}")


def test_fn_name(tool_item: ToolGuardSpecItem) -> str:
    return to_snake_case(f"test_guard_{tool_item.name}")


def test_fn_module_name(tool_item: ToolGuardSpecItem) -> str:
    return to_snake_case(f"test_guard_{tool_item.name}")
