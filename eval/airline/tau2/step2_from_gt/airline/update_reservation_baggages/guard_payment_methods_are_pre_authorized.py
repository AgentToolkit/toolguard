from typing import *
import airline
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline


def guard_payment_methods_are_pre_authorized(history: ChatHistory, api: I_Airline, reservation_id: str, total_baggages: int, nonfree_baggages: int, payment_id: str):
    """
    Policy to check: Before invoking UpdateReservationBaggages, ensure all payment methods such as travel certificates, credit cards, and gift cards appear in the user's profile. Use a maximum of one travel certificate, one credit card, and up to three gift cards per reservation as per company policy.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'
        total_baggages: The updated total number of baggage items included in the reservation.
        nonfree_baggages: The updated number of non-free baggage items included in the reservation.
        payment_id: The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'.
    """
    if not payment_id:
        raise PolicyViolationException("Payment ID must be provided.")

    try:
        reservation_details = api.get_reservation_details(reservation_id)
        user_details = api.get_user_details(reservation_details.user_id)
    except ValueError:
        raise PolicyViolationException("User details or payment methods are not available.")

    if not user_details or not user_details.payment_methods:
        raise PolicyViolationException("Payment methods are not available.")

    payment_methods = user_details.payment_methods

    # Split payment_id into type and id
    payment_type, payment_id = payment_id.split('_', 1)

    # Check if payment method is in user's profile
    if payment_id not in payment_methods:
        raise PolicyViolationException("Payment method is not listed in user's profile.")

    # Count payment methods
    certificate_count = sum(1 for pm in payment_methods.values() if pm.source == 'certificate')
    credit_card_count = sum(1 for pm in payment_methods.values() if pm.source == 'credit_card')
    gift_card_count = sum(1 for pm in payment_methods.values() if pm.source == 'gift_card')

    # Validate policy constraints
    if certificate_count > 1:
        raise PolicyViolationException("More than one travel certificate is not allowed.")
    if credit_card_count > 1:
        raise PolicyViolationException("More than one credit card is not allowed.")
    if gift_card_count > 3:
        raise PolicyViolationException("More than three gift cards are not allowed.")