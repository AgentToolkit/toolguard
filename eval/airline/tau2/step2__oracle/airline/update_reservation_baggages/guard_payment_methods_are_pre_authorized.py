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
    # Retrieve user details
    try:
        reservation = api.get_reservation_details(reservation_id)
        user = api.get_user_details(reservation.user_id)
    except ValueError as e:
        raise PolicyViolationException(f"Error retrieving reservation or user details: {str(e)}")

    # Ensure user details are not None
    if user is None or user.payment_methods is None:
        raise PolicyViolationException("User details or payment methods are not available.")

    # Check if payment method is in user's profile
    if payment_id not in user.payment_methods:
        raise PolicyViolationException("Payment method is not listed in user's profile.")

    # Count payment methods
    travel_certificates = sum(1 for pm in user.payment_methods.values() if isinstance(pm, Certificate))
    credit_cards = sum(1 for pm in user.payment_methods.values() if isinstance(pm, CreditCard))
    gift_cards = sum(1 for pm in user.payment_methods.values() if isinstance(pm, GiftCard))

    # Validate policy constraints
    if travel_certificates > 1:
        raise PolicyViolationException("More than one travel certificate is not allowed.")
    if credit_cards > 1:
        raise PolicyViolationException("More than one credit card is not allowed.")
    if gift_cards > 3:
        raise PolicyViolationException("More than three gift cards are not allowed.")

    # Ensure the provided payment method is valid
    payment_method = user.payment_methods.get(payment_id)
    if payment_method is None:
        raise PolicyViolationException("The provided payment method ID is not valid.")

    # Ensure the payment method is pre-authorized
    if not isinstance(payment_method, (CreditCard, GiftCard, Certificate)):
        raise PolicyViolationException("The payment method is not pre-authorized.")