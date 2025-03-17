
from policy_adherence.types import GenFile, ToolPolicy
from ai_functions import generative

@generative
def _do_generate_tool_tests1(fn_under_test:GenFile, tool:ToolPolicy, domain:GenFile)-> str:
    """Generates Python unit-tests for a given function according to a policy.

    This function generates unit tests to check the implementation of a given function-under-test.
    The function implemtation should assert that ALL policy statements hold on its arguments.
    If the arguments violate a policy statement, an exception should be thrown.
    Policy statement have positive and negative examples.
    For positive-cases, the function should not throw exceptions.
    For negative-cases, the function should throw an exception.
    Generate one test for each example. 

    If an unexpected exception is catched, the test should fail with the nested exception message.

    Name the test using up to 6 representative words (snake_case).

    The function-under-test might call other functions, in the domain, to retreive data, and check the policy accordingly. 
    Hence, you should MOCK the call to other functions and set the expected return value using `unittest.mock.patch`. 
    For example, if `check_book_reservation` is the function-under-test, it may access the `get_user_details()`:
    ```
    args = ...
    user = User(...)
    with patch("check_book_reservation.get_user_details", return_value=user):
    check_book_reservation(args)
    ```

    Make sure to indicate test failures using a meaningful message.

    Args:
        fn (GenFile):

    Returns:
        str: The generated Python 
    """
    ...
