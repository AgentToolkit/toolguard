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
                - API calls are slow. Prefer using simple logic, before calling APIs. API calls are costly in latency. Apply simple logic locally before invoking APIs.
                - If the validation is composed of of multiple disjunctive checks, use the `assert_any_condition_met` function and pass the check functions as parameters.

        **Simple Example: **
        policy_txt = "Limit to five passengers per reservation"
        dependent_tool_names = []
        review_comments=[]

        prev_impl = ```python
    from toolguard.runtime import PolicyViolationException, assert_any_condition_met, rule
    from airline.airline_types import *
    from airline.i_airline import IAirline

    @rule("Limit Five Passengers")
    async def guard_limit_five_passengers(api: IAirline, user_id: str, origin: str, destination: str, flight_type: Literal['round_trip', 'one_way'], cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], passengers: list[Passenger | dict], payment_methods: list[Payment | dict], total_baggages: int, nonfree_baggages: int, insurance: Literal['yes', 'no']):
        \"\"\"
        Policy to check: Limit to five passengers per reservation.

        Args:
            api (IAirline): api to access other tools.
            user_id: The ID of the user to book the reservation such as 'sara_doe_496'.
            origin: The IATA code for the origin city such as 'SFO'.
            destination: The IATA code for the destination city such as 'JFK'.
            flight_type: The type of flight such as 'one_way' or 'round_trip'.
            cabin: The cabin class such as 'basic_economy', 'economy', or 'business'.
            flights: An array of objects containing details about each piece of flight.
            passengers: An array of objects containing details about each passenger.
            payment_methods: An array of objects containing details about each payment method.
            total_baggages: The total number of baggage items to book the reservation.
            nonfree_baggages: The number of non-free baggage items to book the reservation.
            insurance: Whether the reservation has insurance.
        \"\"\"
        pass #FIXME
        ```

        The function should return something like:

        ```python
    from toolguard.runtime import PolicyViolationException, assert_any_condition_met, rule
    from airline.airline_types import *
    from airline.i_airline import IAirline

    @rule("Limit Five Passengers")
    async def guard_limit_five_passengers(api: IAirline, user_id: str, origin: str, destination: str, flight_type: Literal['round_trip', 'one_way'], cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], passengers: list[Passenger | dict], payment_methods: list[Payment | dict], total_baggages: int, nonfree_baggages: int, insurance: Literal['yes', 'no']):
        \"\"\"
        Policy to check: Limit to five passengers per reservation.

        Args:
            api (IAirline): api to access other tools.
            user_id: The ID of the user to book the reservation such as 'sara_doe_496'.
            origin: The IATA code for the origin city such as 'SFO'.
            destination: The IATA code for the destination city such as 'JFK'.
            flight_type: The type of flight such as 'one_way' or 'round_trip'.
            cabin: The cabin class such as 'basic_economy', 'economy', or 'business'.
            flights: An array of objects containing details about each piece of flight.
            passengers: An array of objects containing details about each passenger.
            payment_methods: An array of objects containing details about each payment method.
            total_baggages: The total number of baggage items to book the reservation.
            nonfree_baggages: The number of non-free baggage items to book the reservation.
            insurance: Whether the reservation has insurance.
        \"\"\"

        # Check if the number of passengers exceeds the limit
        if len(passengers) > 5:
            raise PolicyViolationException("More than five passengers are not allowed.")
        ```

        **Composed Example: **
    policy_txt = "at least one of the following conditions must be met: * The airline cancelled the flight. * Business class flights can be cancelled anytime. * cancellation is within 24 hours of booking."
    dependent_tool_names = ["get_reservation_details", "get_flight_status"]
    review_comments=[]

    prev_impl = ```python
    from typing import *
    from toolguard.runtime import PolicyViolationException, assert_any_condition_met, rule
    from airline.airline_types import *
    from airline.i_airline import I_Airline

    @rule("Cancellation Condition Validation")
    async def guard_cancellation_conditions_validation(api: I_Airline, reservation_id: str):
        \"\"\"
        Policy to check: at least one of the following conditions must be met: * The airline cancelled the flight. * Business class flights can be cancelled anytime. * cancellation is within 24 hours of booking.
        \"\"\"
        pass #FIXME
    ```

        The function should return something like:

        ```python
    from typing import *
    from toolguard.runtime import PolicyViolationException, assert_any_condition_met, rule
    from datetime import datetime, timedelta
    from airline.airline_types import *
    from airline.i_airline import I_Airline

    @rule("Cancellation Condition Validation")
    async def guard_cancellation_conditions_validation(api: I_Airline, reservation_id: str):
        \"\"\"
        Policy to check: at least one of the following conditions must be met: * The airline cancelled the flight.  * cancellation is within 24 hours of booking. * Business class flights can be cancelled anytime.
        \"\"\"

        # Get reservation details.
        reservation = await api.get_reservation_details(reservation_id)

        @rule("within_24h")
        def within_24h():
            return (
                datetime.now()
                - datetime.strptime(reservation.created_at, "%Y-%m-%dT%H:%M:%S")
                <= timedelta(hours=24)
            )

        @rule("airline_cancelled")
        async def airline_cancelled():
            for flight in reservation.flights:
                status = await api.get_flight_status(
                    flight.flight_number, flight.date
                )
                if status == "cancelled":
                    return True
            return False

        assert_any_condition_met(
            within_24h,
            airline_cancelled,
        )

        ```
    """
    ...
