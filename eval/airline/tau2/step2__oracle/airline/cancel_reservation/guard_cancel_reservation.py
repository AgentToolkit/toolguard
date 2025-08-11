from typing import *
import airline
from rt_toolguard.data_types import ChatHistory
from airline.airline_types import *
from airline.i_airline import I_Airline

from airline.cancel_reservation.guard_cancellation_policy_for_all_flights import guard_cancellation_policy_for_all_flights
from airline.cancel_reservation.guard_cancellation_of_entire_trips_only import guard_cancellation_of_entire_trips_only


def guard_cancel_reservation(history: ChatHistory, api: I_Airline, reservation_id: str):
    """
    Checks that a tool call complies to the policies.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'.
         
    """
    
    guard_cancellation_policy_for_all_flights(history, api, reservation_id)
    guard_cancellation_of_entire_trips_only(history, api, reservation_id)
