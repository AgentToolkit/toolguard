from typing import *
import airline
from rt_toolguard.data_types import ChatHistory
from airline.airline_types import *
from airline.i_airline import I_Airline

from airline.cancel_reservation.guard_strict_cancellation_rules_enforcement import guard_strict_cancellation_rules_enforcement


def guard_cancel_reservation(history: ChatHistory, api: I_Airline, reservation_id: str):
    """
    Checks that a tool call complies to the policies.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'.
         
    """
    
    guard_strict_cancellation_rules_enforcement(history, api, reservation_id)
