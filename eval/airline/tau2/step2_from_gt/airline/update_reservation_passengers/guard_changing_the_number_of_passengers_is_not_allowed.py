from typing import *
import airline
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_changing_the_number_of_passengers_is_not_allowed(history: ChatHistory, api: I_Airline, reservation_id: str, passengers: list[Passenger | dict]):
    """
    Policy to check: Users are restricted to only updating passenger details such as names or dates of birth within existing reservations. They are not allowed to alter the total number of passengers included in a booking. This limitation applies even when handed over to human agents.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'.
        passengers: An array of objects containing details about each passenger.
    """
    # Fetch the current reservation details using the API
    try:
        current_reservation = api.get_reservation_details(reservation_id)
    except ValueError:
        raise PolicyViolationException("Reservation not found.")

    # Check if the number of passengers in the reservation matches the number of passengers provided
    if len(current_reservation.passengers) != len(passengers):
        raise PolicyViolationException("Altering the total number of passengers in a booking is not allowed.")