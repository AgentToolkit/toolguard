
from typing import List
from policy_adherence.types import SourceFile, ToolPolicy, ToolPolicyItem
from programmatic_ai import generative

model = "gpt-4o-2024-08-06"
@generative(model=model, provider="azure", sdk="litellm")
def generate_policy_item_tests(fn_name:str, fn_src:SourceFile, tool:ToolPolicyItem, domain:SourceFile, dependent_tool_names: List[str])-> str:
    """Generate Python unit tests for a function to verify tool-call compliance with policy constraints.

    This function creates unit tests to validate the behavior of a given function-under-test. 
    The function implementation must ensure that **all policy items** hold for given arguments. 
    If an argument violates a policy item, an exception must be raised.

    **Test Generation Rules:**
    - Each **policy item** has **positive** and **negative** test cases.
    - For **positive cases**, the function-under-test should **not** raise exceptions.
    - For **negative cases**, the function-under-test **must** raise an exception.
    - Each **policy item** gets its own test class.
    - Each **example case** becomes a test method.
    - Test class and method names should be meaningful and use up to **six words in snake_case**.

    **Implementation Notes:**
    - When populating domain objects, make sure to pupulate non-optional fields.
    - Do **not** catch exceptions in tests. Allow them to propagate.
    - You should **mock** the responses from other tools that this tool depends on.
    - You should use `unittest.mock.patch` for mocking other tools with the expected return values.
    
    **Example: Testing the function `check_create_reservation` and mocking `["get_user", "get_hotel"]` tools responses**
    ```python
    args = ...
    user = User(...)
    hotel = Hotel(...)

    with patch("check_create_reservation.get_user", return_value=user):
        with patch("check_create_reservation.get_hotel", return_value=hotel):
            check_book_flight(args)
    ```

    Ensure that test failure messages are meaningful.

    Args:
        fn_name (str): Name of the function under test.
        fn_src (SourceFile): Source code containing the function signature (interface).
        tool (ToolPolicy): Specification of the function-under-test, including positive and negative examples.
        domain (SourceFile): Source code defining available data types and interfaces needed by the tests.
        dependent_tool_names(List[str]): List of other tool names that this tool depends on

    Returns:
        str: Generated Python unit test code.
    """
    ...



model = "gpt-4o-2024-08-06"
@generative(model=model, provider="azure", sdk="litellm")
def tool_information_dependencies(tool_name:str, policy: str, domain:SourceFile)-> List[str]:
    """
    List other tools that the given tool depends on.

    Args:
        tool_name (str): name of the tool under analysis
        policy (str): business policy, in natural language, specifying a constraint on a business processes involving the tool unedr analysis
        domain (SourceFile): Python code defining available data types and other tool interfaces

    Returns:
        str: Generated Python unit test code.

    **Dependency Rules:**
    - Tool available information is: from it function arguments, or from calling other tools.
    - The function analyzes information dependency only on other tools.
    - Information dependency can be only on tools that are immutable. That is, that retieve data only, but do not modify the environment.
    - A dependency in another-tool exists only if the policy mention information is not available in the arguments, but can accessed by calling the other tool.
    - The list of dependencies can be empty, with one, or multiple tools.
    
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
    def buy_car(car:Car, owner_id:str, insurance_id:str):
        pass
    def get_person(id:str) -> Person:
        pass
    def get_insurance(id:str) -> Insurance:
        pass
    def delete_car(car:Car):
        pass
    def list_all_cars_owned_by(id:str): List[Car]
        pass
    "
    }

    assert tool_dependencies(
        "tool_name": "buy_car", 
        "policy": "when buying a new car, you should check that the car owner has a driving licence and that the insurance is valid.",
        "domain": domain
    ) == ["get_person", "get_insurance"]

    assert tool_dependencies(
        "tool_name": "get_insurance", 
        "policy": "when buying a new car, you should check that the car owner has a driving licence and that the insurance is valid.",
        "domain": domain
    ) == []

    assert tool_dependencies(
        "tool_name": "delete_car", 
        "policy": "when buying a new car, you should check that the car owner has a driving licence and that the insurance is valid.",
        "domain": domain
    ) == []

    ```

    """
    ...