
from typing import List, Set
from policy_adherence.data_types import FileTwin, ToolPolicyItem
from programmatic_ai import generative

@generative
async def generate_tool_item_tests(
    fn_under_test_name:str, 
    fn_src: FileTwin, 
    tool_item: ToolPolicyItem, 
    common: FileTwin, 
    domain: FileTwin, 
    dependent_tool_names: Set[str])-> str:
    """Generate Python unit tests for a function to verify tool-call compliance with policy constraints.

    This function creates unit tests to validate the behavior of a given function-under-test. 
    The function goal is to check the argument data, and raise an exception if they violated the requirements in the policy item.

    **Test Generation Rules:**
    - Make sure to Python import all items in fn_src, common and domain modules. Example:
```
from check_my_fn import check_my_function
from common import *
from domain import *
```
    - Each **policy item** has multiple **compliance** and **violation** test examples.
        - For **each compliance example, ONE test method** is generated. 
            - If an exception occurrs in the function-under-test, let the exception propagate up.
        - For **each violation example, ONE test** is generated.
            - the function-under-test is EXPECTED to raise an exception.
            - dont expect a particular error message
        - Test class and method names should be meaningful and use up to **six words in snake_case**.
        - For each test, add a comment quoting the policy item case that this function is testing 
        - Failure message should describe the test scenario that failed, the expected and the actual outcomes.

    **Data population and references:**
    - populate all request object fields that are required by Pydantic or that are required according to the policy.
    - When populating domain objects, use pydantic `.model_construct()`.
    - You should mock the return_value from **ALL tools listed in `dependent_tool_names`**.
    - You should mock the chat_history services. 
    
    **Example:** Testing the function `check_create_reservation`, for policy: `cannot book room for a date in the past`, and mocking dependent_tool_names: `["get_user", "get_hotel"]`
    ```python

    from unittest.mock import MagicMock, patch

    # domain:
    class SomeAPI(Protocol):
        def get_user(self, user_id):
            ...
        def get_hotel(self, hotel_id):
            ...

    # function call arguments
    args = {
        user_id: ...,
        ...
        hotel_id: ....
    }

    # mock the history service:
    history = MagicMock()
    history.ask_bool.return_value = True #Mock that True is the answer to the question

    # mock other tools function return values 
    user = User.model_construct(...)
    hotel = Hotel.model_construct(...)

    api = MagicMock()
    api.get_user.return_value = user
    api.get_hotel.return_value = hotel
    
    #invoke function under test.
    try:
        check_book_flight(args, history, api)
    except Exception as ex:
        # failure message describe the test case
        pytest.fail("The user cannot book room for a date in the past")
    ```

    Args:
        fn_under_test_name (str): the name of the function under test
        fn_src (FileTwin): Source code containing the function-under-test signature.
        tool_item (ToolPolicyItem): Specification of the function-under-test, including positive and negative examples.
        common (FileTwin): utility functions the test may use
        domain (FileTwin): available data types and interfaces needed by the tests.
        dependent_tool_names(Set[str]): other tool names that this tool depends on

    Returns:
        str: Generated Python unit test code.
    """
    ...


@generative
async def improve_tool_tests(prev_impl:FileTwin, domain: FileTwin, tool: ToolPolicyItem, review_comments: List[str])-> str:
    """
    Improve the previous test functions (in Python) to check the given tool policy-items according to the review-comments.

    Args:
        prev_impl (FileTwin): previous implementation of a Python function.
        domain (FileTwin): Python code defining available data types and other tool interfaces.
        tool (ToolPolicyItem): Requirements for this tool.
        review_comments (List[str]): Review comments on the current implementation. For example, pylint errors or Failed unit-tests.

    Returns:
        str: Improved implementation pytest test functions.
    """
    ...


@generative
async def tool_information_dependencies(tool_name:str, policy: str, domain:FileTwin)-> List[str]:
    """
    List other tools that the given tool depends on.

    Args:
        tool_name (str): name of the tool under analysis
        policy (str): business policy, in natural language, specifying a constraint on a business processes involving the tool unedr analysis
        domain (FileTwin): Python code defining available data types and other tool interfaces

    Returns:
        Set[str]: dependent tool names

    **Dependency Rules:**
    - Tool available information is: from it function arguments, or from calling other tools.
    - The function analyzes information dependency only on other tools.
    - Information dependency can be only on tools that are immutable. That is, that retieve data only, but do not modify the environment.
    - A dependency in another-tool exists only if the policy mention information is not available in the arguments, but can accessed by calling the other tool.
    - The set of dependencies can be empty, with one, or multiple tools.
    
    **Example: ** 
```
    domain = {
        "file_name": "domain.py",
        "content": "
    class Car:
        pass
    class Person:
        pass
    class Insurance:
        pass
    class CarAPI(Protocol):
        def buy_car(self, car:Car, owner_id:str, insurance_id:str):
            pass
        def get_person(self, id:str) -> Person:
            pass
        def get_insurance(self, id:str) -> Insurance:
            pass
        def delete_car(self, car:Car):
            pass
        def list_all_cars_owned_by(self, id:str): List[Car]
            pass
    "
    }

    # According to the policy, the `buy_car` operation depends on `get_person` to get the driving licence of the owner, and on `get_insurance` to check the insurance is valid.
    assert tool_dependencies(
        "tool_name": "buy_car", 
        "policy": "when buying a new car, you should check that the car owner has a driving licence and that the insurance is valid.",
        "domain": domain
    ) == {"get_person", "get_insurance"}

    # According to the policy, the `get_insurance` operation does not depend on any other operation
    assert tool_dependencies(
        "tool_name": "get_insurance", 
        "policy": "when buying a new car, you should check that the car owner has a driving licence and that the insurance is valid.",
        "domain": domain
    ) == {}

    # According to the policy, the `delete_car` operation does not depend on any other operation
    assert tool_dependencies(
        "tool_name": "delete_car", 
        "policy": "when buying a new car, you should check that the car owner has a driving licence and that the insurance is valid.",
        "domain": domain
    ) == {}

    ```

    """
    ...


@generative
async def improve_tool_check_fn(prev_impl:FileTwin, domain: FileTwin, policy_item: ToolPolicyItem, review_comments: List[str])-> str:
    """
    Improve the previous tool-call check implementation (in Python) to cover all tool policy-items according to the review-comments.

    Args:
        prev_impl (FileTwin): previous implementation of the tool-call check.
        domain (FileTwin): Python code defining available data types and other tool interfaces.
        policy_item (ToolPolicyItem): Requirements for this tool.
        review_comments (List[str]): Review comments on the current implementation. For example, pylint errors or Failed unit-tests.

    Returns:
        str: Improved implementation of the tool-call check.

    **Implementation Rules:**"
    - Do not change the function signature.
    - ALL tool policy items must be validated on the tool arguments.
    - The code should be simple.
    - The code should be well documented.
    - You should just validate the tool-call. You should never call the tool itself.
    - If needed, you may use the `api` interface to get additional information from the backend.
    - If needed, you may call `history.ask(question)` or `history.ask_bool(question)` services to check if some interaction happened in this chat. Your question should be clear. For example: "did the user confirm the agent suggestion?".
    - History services are slow and expensive. Prefer calling domain functions over history services.
    """
    ...