from typing import *
import airline
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_only_adding_checked_bags_is_allowed(history: ChatHistory, api: I_Airline, reservation_id: str, total_baggages: int, nonfree_baggages: int, payment_id: str):
    """
    Policy to check: You can update the baggage information of an existing reservation, allowing users to add additional checked bags. Removing checked bags from the reservation is not permitted. Ensure the payment method for any additional non-free baggage is provided at invocation.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'
        total_baggages: The updated total number of baggage items included in the reservation.
        nonfree_baggages: The updated number of non-free baggage items included in the reservation.
        payment_id: The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'.
    """
    # Retrieve the current reservation details
    reservation = api.get_reservation_details(reservation_id)

    # Check if the total baggage count is being reduced
    if total_baggages < reservation.total_baggages:
        raise PolicyViolationException("Removing checked bags from the reservation is not permitted.")

    # Ensure payment method is provided for non-free baggage
    if nonfree_baggages > reservation.nonfree_baggages and not payment_id:
        raise PolicyViolationException("Payment method for additional non-free baggage must be provided.")