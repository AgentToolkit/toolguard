from typing import *
import airline
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_validate_passenger_number_consistency(history: ChatHistory, api: I_Airline, reservation_id: str, passengers: list[Passenger | dict]):
    """
    Policy to check: When modifying passenger details in a reservation using ToolX, ensure the number of passengers remains the same. You can change details like name or date of birth, but the total number must not be altered. This rule is critical and an exception cannot be made, even by human agents.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'.
        passengers: An array of objects containing details about each passenger.
    Raises:
        PolicyViolationException: If the number of passengers is changed.
    """
    # Get the original reservation details using the API
    reservation = api.get_reservation_details(reservation_id)
    original_count = len(reservation.passengers)
    new_count = len(passengers)
    # Check if the number of passengers is changed
    if new_count != original_count:
        raise PolicyViolationException(
            f"Passenger count changed from {original_count} to {new_count}. This is not allowed by policy."
        )
