# mypy: ignore-errors

from typing import List

from mellea import generative

from toolguard.runtime.data_types import FileTwin


@generative
async def improve_tool_guard(
    prev_impl: str,
    policy_txt: str,
    dependent_tool_names: List[str],
    review_comments: List[str],
    api: FileTwin,
    data_types: FileTwin,
) -> str:
    """
        Improve the previous tool-call guard implementation (in Python) so that it fully adheres to the given policy and addresses all review comments.

        Args:
            prev_impl (str): The previous implementation of the tool-call check.
            policy_txt (str): Requirements for this tool.
            dependent_tool_names (List[str]): Names of other tools that this tool may call to obtain required information.
            review_comments (List[str]): Review feedback on the current implementation (e.g., pylint errors, failed unit tests).
            api (FileTwin): Python code defining available APIs.
            data_types (FileTwin): Python code defining available data types.

        Returns:
            str: The improved implementation of the tool-call check.

        Implementation Rules:
            - Never modify the function signature. Do not add, remove or change the parameters, their type annotations, async modifier of the function .
            - All policy requirements must be validated.
            - Keep the implementation simple and well-documented.
            - Only validate the tool-call arguments; never call the tool itself.
            - If additional information is needed beyond the function arguments, use only the APIs of tools listed in `dependent_tool_names`.
            - Generate code that enforces the given policy only, do not generate any additional logic that is not explicitly mentioned in the policy.

        **Example: **
    prev_impl = ```python
    from typing import *
    from airline.airline_types import *
    from airline.i_airline import I_Airline

    async def guard_Checked_Bag_Allowance_by_Membership_Tier(api: I_Airline, user_id: str, passengers: list[Passenger]):
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

    async def guard_Checked_Bag_Allowance_by_Membership_Tier(api: I_Airline, user_id: str, passengers: list[Passenger]):
        \"\"\"
        Limit to five passengers per reservation.
        \"\"\"
        if len(passengers) > 5:
            raise PolicyViolationException("More than five passengers are not allowed.")
    ```
    """
    ...
