
from policy_adherence.types import SourceFile, ToolPolicy
from programmatic_ai import generative

model = "gpt-4o-2024-08-06"
@generative(model=model, provider="azure", sdk="litellm")
def generate_toolcheck_tests(fn_name:str, fn_src:SourceFile, tool:ToolPolicy, domain:SourceFile)-> str:
    """Generates Python unit tests for a function to verify tool-call compliance with policy constraints.

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
    - The function-under-test may call domain functions to retrieve data to enforce policies.
    - **Mock** domain function calls using `unittest.mock.patch` and set expected return values.
    
    **Example: Mocking Domain Function Calls**
    If `check_update_reservation()` is the function-under-test and depends on `get_user()`, mock it as follows:
    
    ```python
    args = {...}
    user = User(...)
    with patch("check_update_reservation.get_user", return_value=user):
        check_update_reservation(args)
    ```

    **Ensure that test failure messages are meaningful.**

    Args:
        fn_name (str): Name of the function under test.
        fn_src (SourceFile): Source code containing the function signature (interface).
        tool (ToolPolicy): Specification of the function-under-test, including positive and negative examples.
        domain (SourceFile): Source code defining available data types and interfaces needed by the tests.

    Returns:
        str: Generated Python unit test code.
    """
    ...
