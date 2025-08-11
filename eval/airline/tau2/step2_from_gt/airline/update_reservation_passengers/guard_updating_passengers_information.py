from typing import *
import airline
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_updating_passengers_information(history: ChatHistory, api: I_Airline, reservation_id: str, passengers: list[Passenger | dict]):
    """
    Policy to check: Ensure all passengers including first name, last name, and date of birth.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'.
        passengers: An array of objects containing details about each passenger.
    """
    for passenger in passengers:
        if isinstance(passenger, dict):
            first_name = passenger.get('first_name')
            last_name = passenger.get('last_name')
            dob = passenger.get('dob')
        else:
            first_name = passenger.first_name
            last_name = passenger.last_name
            dob = passenger.dob

        if not first_name:
            raise PolicyViolationException("Missing first name for a passenger.")
        if not last_name:
            raise PolicyViolationException("Missing last name for a passenger.")
        if not dob:
            raise PolicyViolationException("Missing date of birth for a passenger.")