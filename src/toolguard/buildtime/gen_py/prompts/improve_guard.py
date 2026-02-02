# mypy: ignore-errors

from typing import List

from mellea import generative

from toolguard.runtime.data_types import FileTwin


@generative
async def improve_tool_guard(
    policy_txt: str,
    dependent_tool_names: List[str],
    prev_impl: str,
    review_comments: List[str],
    api: FileTwin,
    data_types: FileTwin,
) -> str:
    """
        Improve the previous tool-call guard implementation (in Python) so that it fully adheres to the given policy and addresses all review comments.

        Args:
            policy_txt (str): Requirements for this tool.
            dependent_tool_names (List[str]): Names of other tools that this tool may call to obtain required information.
            prev_impl (str): The previous implementation of the tool-call check.
            review_comments (List[str]): Review feedback on the current implementation (e.g., pylint errors, failed unit tests).
            api (FileTwin): Python code defining available APIs.
            data_types (FileTwin): Python code defining available data types.

        Returns:
            str: The improved implementation of the tool-call check.

        Implementation Rules:
            - Never modify the function signature. Do not add, remove or change the parameters, their type annotations.
            - All policy requirements must be validated.
            - Keep the implementation simple and well-documented.
            - Only validate the tool-call arguments; never call the tool itself.
            - Generate code that enforces the given policy only.
            - Do not generate any additional logic that is not explicitly mentioned in the policy.
            - If additional information is needed beyond the function arguments, use only the APIs of tools listed in `dependent_tool_names`.
            - Remote API calls are slow. Prefer using simple logic, before calling remote APIs.Remote API calls are costly in latency. Apply simple logic locally before invoking remote APIs.

        **Example: **
    policy_txt = "at least one of the following conditions must be met: * The airline cancelled the flight. * Business class flights can be cancelled anytime. * cancellation is within 24 hours of booking."
    dependent_tool_names = ["get_reservation_details", "get_flight_status"]
    review_comments=[]
    prev_impl = ```python
    from typing import *
    from toolguard.runtime import PolicyViolationException

    from airline.airline_types import *
    from airline.i_airline import I_Airline

    async def guard_cancellation_conditions_validation(api: I_Airline, reservation_id: str):
        \"\"\"
        Policy to check: at least one of the following conditions must be met: * The airline cancelled the flight. * Business class flights can be cancelled anytime. * cancellation is within 24 hours of booking.
        \"\"\"
        pass #FIXME
    ```

    The function should return something like:

    ```python
    from typing import *
    from toolguard.runtime import PolicyViolationException
    from datetime import datetime, timedelta
    from airline.airline_types import *
    from airline.i_airline import I_Airline

    async def guard_cancellation_conditions_validation(api: I_Airline, reservation_id: str):
        \"\"\"
        Policy to check: at least one of the following conditions must be met: * The airline cancelled the flight.  * cancellation is within 24 hours of booking. * Business class flights can be cancelled anytime.
        \"\"\"

        # Get reservation details.
        reservation = await api.get_reservation_details(reservation_id)

        # Business class flights can be cancelled anytime
        if reservation.cabin == 'business':
            return

        # Cancellation within 24 hours of booking
        created_at = datetime.fromisoformat(reservation.created_at)
        now = datetime.now()
        if now - created_at <= timedelta(hours=24):
            return

        # Airline cancelled the flight
        for flight in reservation.flights:
            flight_status = await api.get_flight_status(flight.flight_number, flight.date)
            if 'canceled' == flight_status.lower():
                return

        raise PolicyViolationException("Cancellation not allowed. None of the required conditions are met.")
    ```
    Note: the remote api call `api.get_reservation_details()` is needed for all conditions.
    But the call to `api.get_flight_status()` is defered until the first two conditions are not met.

    """
    ...
