from typing import *
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_user_confirmation_before_database_update(
    history: ChatHistory,
    api: I_Airline,
    user_id: str,
    origin: str,
    destination: str,
    flight_type: Literal['round_trip', 'one_way'],
    cabin: Literal['business', 'economy', 'basic_economy'],
    flights: list[FlightInfo | dict],
    passengers: list[Passenger | dict],
    payment_methods: list[Payment | dict],
    total_baggages: int,
    nonfree_baggages: int,
    insurance: Literal['yes', 'no']
):
    """
    Policy to check: Ensure that before using ToolX for database updates related to booking a reservation, changing flight details, passenger information, baggage edits, or cabin upgrades, you must present the details of these actions to the user and obtain a clear affirmative confirmation ('yes') from the user before proceeding.

    This guard checks that explicit user confirmation ('yes') was obtained before proceeding with any database update action.
    If confirmation is missing, a PolicyViolationException is raised.
    """
    # Ask the chat history if the user has given an explicit 'yes' confirmation for the presented details
    confirmed = history.ask_bool(
        "Did the user give an explicit 'yes' confirmation after being presented with all details of the intended booking or update action?"
    )
    if not confirmed:
        raise PolicyViolationException(
            "Explicit user confirmation ('yes') was not obtained before performing a database update."
        )
