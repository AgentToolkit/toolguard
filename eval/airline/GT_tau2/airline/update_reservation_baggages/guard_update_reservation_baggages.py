from typing import *
import airline
from rt_toolguard.data_types import ChatHistory
from airline.airline_types import *
from airline.i_airline import I_Airline

from airline.update_reservation_baggages.guard_obtain_user_and_reservation_ids import guard_obtain_user_and_reservation_ids
from airline.update_reservation_baggages.guard_only_adding_checked_bags_is_allowed import guard_only_adding_checked_bags_is_allowed
from airline.update_reservation_baggages.guard_payment_methods_are_pre_authorized import guard_payment_methods_are_pre_authorized
from airline.update_reservation_baggages.guard_charge_for_extra_baggage_items import guard_charge_for_extra_baggage_items


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
    
    # guard_obtain_user_and_reservation_ids(history, api, reservation_id, total_baggages, nonfree_baggages, payment_id)
    guard_only_adding_checked_bags_is_allowed(history, api, reservation_id, total_baggages, nonfree_baggages, payment_id)
    guard_payment_methods_are_pre_authorized(history, api, reservation_id, total_baggages, nonfree_baggages, payment_id)
    guard_charge_for_extra_baggage_items(history, api, reservation_id, total_baggages, nonfree_baggages, payment_id)
