from typing import *
import airline
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_charge_for_extra_baggage_items(history: ChatHistory, api: I_Airline, reservation_id: str, total_baggages: int, nonfree_baggages: int, payment_id: str):
    """
    Policy to check: To use the UpdateReservationBaggages tool effectively, verify the user's membership level (regular, silver, or gold) and cabin class (basic economy, economy, business). This will determine the number of free checked bags allowed. Charge $50 for each additional baggage item beyond the free allowance according to the user's membership and cabin class entitlements.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'
        total_baggages: The updated total number of baggage items included in the reservation.
        nonfree_baggages: The updated number of non-free baggage items included in the reservation.
        payment_id: The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'.
    """
    # Retrieve reservation details
    try:
        reservation_details = api.get_reservation_details(reservation_id)
    except ValueError:
        raise PolicyViolationException("Reservation details not found for the given reservation ID.")

    # Retrieve user details using user_id from reservation
    user_id = reservation_details.user_id
    try:
        user_details = api.get_user_details(user_id)
    except ValueError:
        raise PolicyViolationException("User details not found for the given user ID.")

    # Determine free baggage allowance based on membership and cabin class
    membership = user_details.membership
    cabin_class = reservation_details.cabin

    free_baggage_allowance = 0
    if membership == 'regular':
        if cabin_class == 'basic_economy':
            free_baggage_allowance = 0
        elif cabin_class == 'economy':
            free_baggage_allowance = 1
        elif cabin_class == 'business':
            free_baggage_allowance = 2
    elif membership == 'silver':
        if cabin_class == 'basic_economy':
            free_baggage_allowance = 1
        elif cabin_class == 'economy':
            free_baggage_allowance = 2
        elif cabin_class == 'business':
            free_baggage_allowance = 3
    elif membership == 'gold':
        if cabin_class == 'basic_economy':
            free_baggage_allowance = 2
        elif cabin_class == 'economy':
            free_baggage_allowance = 3
        elif cabin_class == 'business':
            free_baggage_allowance = 3

    # Calculate the number of excess baggages
    excess_baggages = total_baggages - free_baggage_allowance

    # Check if the number of non-free baggages matches the excess baggages
    if nonfree_baggages != excess_baggages:
        raise PolicyViolationException("Incorrect number of non-free baggages.")

    # Calculate the expected charge for excess baggages
    expected_charge = excess_baggages * 50

    # Verify payment method
    payment_methods = user_details.payment_methods
    if payment_id not in payment_methods:
        raise PolicyViolationException("Invalid payment method.")

    # Ensure the payment method can cover the expected charge
    payment_method = payment_methods[payment_id]
    if isinstance(payment_method, GiftCard) and payment_method.amount < expected_charge:
        raise PolicyViolationException("Insufficient gift card balance.")
    elif isinstance(payment_method, Certificate) and payment_method.amount < expected_charge:
        raise PolicyViolationException("Insufficient certificate balance.")

    # Ensure the payment method is valid for the expected charge
    if isinstance(payment_method, CreditCard):
        # Assuming credit card can always cover the charge
        pass
    else:
        raise PolicyViolationException("Invalid payment method type for the charge.")

    # If all checks pass, the tool-call is valid