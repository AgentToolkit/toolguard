from typing import *
import airline
from rt_toolguard.data_types import ChatHistory
from airline.airline_types import *
from airline.i_airline import I_Airline

from airline.update_reservation_baggages.guard_explicit_confirmation_for_baggage_update import guard_explicit_confirmation_for_baggage_update
from airline.update_reservation_baggages.guard_baggage_addition_policy import guard_baggage_addition_policy
from airline.update_reservation_baggages.guard_payment_method_validation_for_baggage_update import guard_payment_method_validation_for_baggage_update


def guard_update_reservation_baggages(history: ChatHistory, api: I_Airline, reservation_id: str, total_baggages: int, nonfree_baggages: int, payment_id: str):
    """
    Checks that a tool call complies to the policies.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'
        total_baggages: The updated total number of baggage items included in the reservation.
        nonfree_baggages: The updated number of non-free baggage items included in the reservation.
        payment_id: The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'.
         
    """
    
    guard_explicit_confirmation_for_baggage_update(history, api, reservation_id, total_baggages, nonfree_baggages, payment_id)
    guard_baggage_addition_policy(history, api, reservation_id, total_baggages, nonfree_baggages, payment_id)
    guard_payment_method_validation_for_baggage_update(history, api, reservation_id, total_baggages, nonfree_baggages, payment_id)
