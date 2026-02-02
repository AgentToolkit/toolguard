import inspect
from typing import Any, Callable, Awaitable
from contextvars import ContextVar
from functools import wraps
from loguru import logger


#: Context variable that maintains the current stack of rule names being evaluated.
#: Used by RuleScope to track hierarchical rule execution. The value is a tuple
#: of rule names, where each element represents a level in the rule call stack.
current_rule: ContextVar[tuple[str, ...]] = ContextVar("current_rule", default=())


class RuleScope:
    """Context manager for tracking rule execution scope.

    This class manages the hierarchical scope of rule execution by maintaining
    a stack of rule names in the current_rule context variable. It's used as a
    context manager to track which rules are currently being evaluated.

    Args:
        rule_name: The name of the rule being entered.
    """

    def __init__(self, rule_name: str):
        self.rule_name = rule_name
        self._token: Any = None

    def __enter__(self):
        parent = current_rule.get()
        self._token = current_rule.set(parent + (self.rule_name,))
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._token is not None:
            current_rule.reset(self._token)
        return False


def rule(name: str):
    """Decorator to mark a function as a rule and track its execution scope.

    This decorator wraps both synchronous and asynchronous functions to execute
    them within a RuleScope context, which tracks the currently executing rule
    using context variables.

    Args:
        name: The name of the rule to be tracked during execution.

    Returns:
        A decorator function that wraps the target function with rule scope tracking.

    Example:
        @rule("validation_rule")
        def validate_data(data):
            # Function logic here
            pass

        @rule("async_validation_rule")
        async def async_validate_data(data):
            # Async function logic here
            pass
    """

    def decorator(fn):
        @wraps(fn)
        async def async_wrapper(*args, **kwargs):
            with RuleScope(name):
                return await fn(*args, **kwargs)

        @wraps(fn)
        def sync_wrapper(*args, **kwargs):
            with RuleScope(name):
                return fn(*args, **kwargs)

        return async_wrapper if inspect.iscoroutinefunction(fn) else sync_wrapper

    return decorator


async def ORLogic(*checks: Callable[[], bool | Awaitable[bool]]):
    """
    Evaluate checks left-to-right.
    Return True on first truthy result.
    Exceptions are treated as False.
    """
    for check in checks:
        try:
            result = check()
            if inspect.isawaitable(result):
                result = await result

            if result:
                return True

        except Exception as e:
            logger.warning(
                "OR condition failed, ignoring",
                extra={
                    "check": getattr(check, "__name__", repr(check)),
                    "error": str(e),
                },
            )
            continue

    return False
