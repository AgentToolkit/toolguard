from typing import Any, Callable, Dict, List

# Type alias for tool definitions that can be provided in two formats:
# - List[Callable]: A list of Python callable functions
# - Dict[str, Any]: An OpenAPI specification dictionary
TOOLS = List[Callable] | Dict[str, Any]
