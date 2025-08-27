
from typing import List, Set
from toolguard.data_types import Domain, ToolPolicyItem
from programmatic_ai import generative

from toolguard.gen_py.prompts.python_code import PythonCodeModel

@generative
async def improve_tool_guard(prev_impl: PythonCodeModel, domain: Domain, policy_item: ToolPolicyItem, dependent_tool_names: List[str], review_comments: List[str])-> PythonCodeModel:
    """
    Improve the previous tool-call guard implementation (in Python) so that it fully adheres to the given policy and addresses all review comments.

    Args:
        prev_impl (PythonCodeModel): The previous implementation of the tool-call check.
        domain (Domain): Python code defining available data types and other tool interfaces.
        policy_item (ToolPolicyItem): Requirements for this tool.
        dependent_tool_names (List[str]): Names of other tools that this tool may call to obtain required information.
        review_comments (List[str]): Review feedback on the current implementation (e.g., pylint errors, failed unit tests).

    Returns:
        PythonCodeModel: The improved implementation of the tool-call check.

    Implementation Rules:
        - Do not modify the function signature, parameter names, or type annotations.
        - All policy requirements must be validated.
        - Keep the implementation simple and well-documented.
        - Only validate the tool-call arguments; never call the tool itself.
        - If additional information is needed beyond the function arguments, use only the APIs of tools listed in `dependent_tool_names`.

    **Example: ** 
prev_impl = ```python
from typing import *
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_Checked_Bag_Allowance_by_Membership_Tier(api: I_Airline, user_id: str, passengers: list[Passenger]):
    \"\"\"
    Limit to five passengers per reservation.
    \"\"\"
    pass #FIXME
```

should return something like:
```python
from typing import *
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_Checked_Bag_Allowance_by_Membership_Tier(api: I_Airline, user_id: str, passengers: list[Passenger]):
    \"\"\"
    Limit to five passengers per reservation.
    \"\"\"
    if len(passengers) > 5:
        raise PolicyViolationException("More than five passengers are not allowed.")
```
    """
    ...