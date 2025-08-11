from typing import *
import airline
from rt_toolguard.data_types import ChatHistory
from airline.airline_types import *
from airline.i_airline import I_Airline

from airline.update_reservation_passengers.guard_updating_passengers_information import guard_updating_passengers_information
from airline.update_reservation_passengers.guard_changing_the_number_of_passengers_is_not_allowed import guard_changing_the_number_of_passengers_is_not_allowed


def guard_update_reservation_passengers(history: ChatHistory, api: I_Airline, reservation_id: str, passengers: list[Passenger | dict]):
    """
    Checks that a tool call complies to the policies.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'.
        passengers: An array of objects containing details about each passenger.
         
    """
    
    guard_updating_passengers_information(history, api, reservation_id, passengers)
    guard_changing_the_number_of_passengers_is_not_allowed(history, api, reservation_id, passengers)
