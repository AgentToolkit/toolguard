
from typing import List, Set
from toolguard.data_types import Domain, FileTwin, ToolPolicyItem
from programmatic_ai import generative

from toolguard.gen_py.prompts.python_code import PythonCodeModel

@generative
async def generate_tool_item_tests(
    fn_under_test_name: str, 
    fn_src: FileTwin, 
    tool_item: ToolPolicyItem, 
    domain: Domain, 
    dependent_tool_names: Set[str])-> PythonCodeModel:
    """
    Generate Python unit tests for a function to verify tool-call compliance with policy constraints.

    This function creates unit tests to validate the behavior of a given function-under-test. 
    The function goal is to check the argument data, and raise an exception if they violated the requirements in the policy item.

    **Test Generation Rules:**
    - Make sure to Python import all items in fn_src, common and domain modules.
    - Each `tool_item` has multiple `compliance_examples` and `violation_examples` examples.
        - For each `compliance_examples`, ONE test method is generated. 
        - For each `violation_examples`, ONE test method is generated.
            - The function-under-test is EXPECTED to raise a `PolicyViolationException`.
            - use `with pytest.raises(PolicyViolationException): function_under_test()` to expect for exceptions.
            
        - Test class and method names should be meaningful and use up to **six words in snake_case**.
        - For each test, add a comment quoting the policy item case that this function is testing 
        - Failure message should describe the test scenario that failed, the expected and the actual outcomes.

    **Data population and references:**
    - For compliance examples, populate all fields. 
        - For collections (arrays, dict and sets) populate at least one item.
    - You should mock the return_value from ALL tools listed in `dependent_tool_names`. 
        - Use `side_effect` to return the expected value only when the expected parameters are passed.
    - For time dependent attributes, compute the timestamp dynamically (avoid hardcoded times).
        - for example, to set a timestamp occurred 24 hours ago, use something like: `created_at = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")`.
        - import the required date and time libraries. for example: `from datetime import datetime, timedelta`
    - You should also mock the chat_history services.
    - If you have a choice passing a plain a Pydantic model or a `Dictionary`, prefer Pydantic.
    
    **Example:** Testing the function `check_create_reservation`, 
    * Policy: `cannot book a room for a date in the past`
    * Violation example: `book a room for a hotel, one week ago`
    * Dependent_tool_names: `["get_user", "get_hotel"]`
    * Domain: 
```python
# file: my_app/api.py
class SomeAPI(ABC):
    def get_user(self, user_id):
        ...
    def get_hotel(self, hotel_id):
        ...
    def create_reservation(self, user_id: str, hotel_id: str, reservation_date: str, persons: int):
        \"\"\"
        Args:
            ...
            reservation_date: check in date, in `YYYY-MM-DDTHH:MM:SS` format
        \"\"\"
        ...
```
    * fn_under_test_name: `guard_create_reservation`
    * fn_src:
```python
# file: my_app/guard_create_reservation.py
def guard_create_reservation(history: ChatHistory, api: SomeAPI, user_id: str, hotel_id: str, reservation_date: str, persons: int):
    ...
```

    Should return this snippet:
```python
from unittest.mock import MagicMock, patch
import pytest
from toolguard.data_types import PolicyViolationException
from my_app.guard_create_reservation import guard_create_reservation
from my_app.api import *

def test_book_in_the_past():
    \"\"\" 
    Policy: "cannot book room for a date in the past"
    Example: "book a room for a hotel, one week ago"
    \"\"\" 
    
    # mock the history service:
    history = MagicMock()
    history.ask_bool.return_value = True #Mock that True is the answer to the question

    # mock other tools function return values 
    user = User(user_id="123", ...)
    hotel = Hotel(hotel_id="789", ...)

    api = MagicMock(spec=SomeAPI)
    api.get_user.side_effect = lambda user_id: user if user_id == "123" else None
    api.get_hotel.side_effect = lambda hotel_id: hotel if hotel_id == "789" else None
    
    #invoke function under test.
    with pytest.raises(PolicyViolationException):
        next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
        check_create_reservation(user_id="123", hotel_id="789", reservation_date=next_week, persons=3, history, api)
```

    Args:
        fn_under_test_name (str): the name of the function under test
        fn_src (FileTwin): Source code containing the function-under-test signature.
        tool_item (ToolPolicyItem): Specification of the function-under-test, including positive and negative examples.
        domain (Domain): available data types and interfaces the test can use.
        dependent_tool_names(Set[str]): other tool names that this tool depends on

    Returns:
        PythonCodeModel: Generated Python unit test code.
    """
    ...


@generative
async def improve_tool_tests(
    prev_impl: PythonCodeModel, 
    domain: Domain, 
    policy_item: ToolPolicyItem, 
    review_comments: List[str])-> PythonCodeModel:
    """
    Improve the previous test functions (in Python) to check the given tool policy-items according to the review-comments.
    **Implementation Rules:**"
    - Do not change the function signature.
    - You can add import statements, but ont remove them.

    Args:
        prev_impl (PythonCodeModel): previous implementation of a Python function.
        domain (Domain): Python source code defining available data types and APIs that the test can use.
        tool (ToolPolicyItem): Requirements for this tool.
        review_comments (List[str]): Review comments on the current implementation. For example, pylint errors or Failed unit-tests.

    Returns:
        PythonCodeModel: Improved implementation pytest test functions.
    """
    ...
