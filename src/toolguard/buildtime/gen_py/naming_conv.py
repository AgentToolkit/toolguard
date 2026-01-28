from toolguard.buildtime.utils import py
from toolguard.runtime.data_types import ToolGuardSpec, ToolGuardSpecItem


def guard_fn_name(tool_policy: ToolGuardSpec) -> str:
    return py.to_py_func_name(f"guard_{tool_policy.tool_name}")


def guard_fn_module_name(tool_policy: ToolGuardSpec) -> str:
    return py.to_py_module_name(f"guard_{tool_policy.tool_name}")


def guard_item_fn_name(tool_item: ToolGuardSpecItem) -> str:
    return py.to_py_func_name(f"guard_{tool_item.name}")


def guard_item_fn_module_name(tool_item: ToolGuardSpecItem) -> str:
    return py.to_py_module_name(f"guard_{tool_item.name}")


def test_fn_name(tool_item: ToolGuardSpecItem) -> str:
    return py.to_py_func_name(f"test_guard_{tool_item.name}")


def test_fn_module_name(tool_item: ToolGuardSpecItem) -> str:
    return py.to_py_module_name(f"test_guard_{tool_item.name}")
