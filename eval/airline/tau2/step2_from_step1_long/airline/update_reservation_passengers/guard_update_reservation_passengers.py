from typing import *
import airline
from rt_toolguard.data_types import ChatHistory
from airline.airline_types import *
from airline.i_airline import I_Airline

from airline.update_reservation_passengers.guard_ensure_user_confirmation import guard_ensure_user_confirmation
from airline.update_reservation_passengers.guard_validate_passenger_number_consistency import guard_validate_passenger_number_consistency
from airline.update_reservation_passengers.guard_transfer_requirement_for_human_assistance import guard_transfer_requirement_for_human_assistance


def guard_update_reservation_passengers(history: ChatHistory, api: I_Airline, reservation_id: str, passengers: list[Passenger | dict]):
    """
    Checks that a tool call complies to the policies.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'.
        passengers: An array of objects containing details about each passenger.
         
    """
    
    guard_ensure_user_confirmation(history, api, reservation_id, passengers)
    guard_validate_passenger_number_consistency(history, api, reservation_id, passengers)
    guard_transfer_requirement_for_human_assistance(history, api, reservation_id, passengers)
