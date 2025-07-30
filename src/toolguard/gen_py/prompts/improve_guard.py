
from typing import List
from toolguard.data_types import Domain, ToolPolicyItem
from programmatic_ai import generative

from toolguard.gen_py.prompts.python_code import PythonCodeModel

@generative
async def improve_tool_guard_fn(prev_impl: PythonCodeModel, domain: Domain, policy_item: ToolPolicyItem, review_comments: List[str])-> PythonCodeModel:
    """
    Improve the previous tool-call guard implementation (in Python) to cover all tool policy-items according to the review-comments.

    Args:
        prev_impl (PythonCodeModel): previous implementation of the tool-call check.
        domain (Domain): Python code defining available data types and other tool interfaces.
        policy_item (ToolPolicyItem): Requirements for this tool.
        review_comments (List[str]): Review comments on the current implementation. For example, pylint errors or Failed unit-tests.

    Returns:
        PythonCodeModel: Improved implementation of the tool-call check.

    **Implementation Rules:**"
    - Do not change the function signature.
    - ALL tool policy items must be validated on the tool arguments.
    - The code should be simple.
    - The code should be well documented.
    - You should just validate the tool-call. You should never call the tool itself.
    - If needed, you may use the `api` interface to get additional information from the backend.
    - If needed, you may call `history.ask(question)` or `history.ask_bool(question)` services to check if some interaction happened in this chat. Your question should be clear. For example: "did the user confirm the agent suggestion?".
    - History services are slow and expensive. Prefer calling domain functions over history services.

    **Example: ** 
prev_impl = ```python
from typing import *
from rt_toolguard.data_types import ChatHistory
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_Checked_Bag_Allowance_by_Membership_Tier(history: ChatHistory, api: I_Airline, user_id: str, origin: str, destination: str, flight_type: Literal['one_way', 'round_trip'], cabin: Literal['basic_economy', 'economy', 'business'], flights: list[dict[str, str]], passengers: list[dict[str, str]], payment_methods: list[dict[str, float]], total_baggages: int, nonfree_baggages: int, insurance: Literal['yes', 'no']):
    \"\"\"
    Checks that a tool call complies with the following policy:
    Limit to five passengers per reservation.
    \"\"\"
    pass #FIXME
```
should return something like:
```python
from typing import *
from rt_toolguard.data_types import ChatHistory
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_Checked_Bag_Allowance_by_Membership_Tier(history: ChatHistory, api: I_Airline, user_id: str, origin: str, destination: str, flight_type: Literal['one_way', 'round_trip'], cabin: Literal['basic_economy', 'economy', 'business'], flights: list[dict[str, str]], passengers: list[dict[str, str]], payment_methods: list[dict[str, float]], total_baggages: int, nonfree_baggages: int, insurance: Literal['yes', 'no']):
    \"\"\"
    Checks that a tool call complies with the following policy:
    Limit to five passengers per reservation.
    \"\"\"
    if len(passengers) > 5:
        raise PolicyViolationException("More than five passengers are not allowed.")
```
    """
    ...