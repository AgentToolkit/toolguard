from toolguard.runtime.data_types import ToolGuardSpec, ToolGuardSpecItem
from toolguard.buildtime.utils.str import to_snake_case


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
