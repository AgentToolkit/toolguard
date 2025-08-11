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
    # Retrieve user and reservation details
    reservation = api.get_reservation_details(reservation_id)
    user = api.get_user_details(reservation.user_id)

    # Determine free baggage allowance based on membership and cabin class
    free_baggage_allowance = {
        'regular': {'basic_economy': 0, 'economy': 1, 'business': 2},
        'silver': {'basic_economy': 1, 'economy': 2, 'business': 3},
        'gold': {'basic_economy': 2, 'economy': 3, 'business': 3}
    }

    # Get the user's membership level and cabin class
    membership_level = user.membership
    cabin_class = reservation.cabin

    # Calculate the allowed free baggage
    allowed_free_baggage = free_baggage_allowance[membership_level][cabin_class]

    # Calculate the expected non-free baggage
    expected_nonfree_baggages = max(0, total_baggages - allowed_free_baggage)

    # Check if the non-free baggage count matches the expected count
    if nonfree_baggages != expected_nonfree_baggages:
        raise PolicyViolationException("Incorrect number of non-free baggages charged.")

    # Check if the payment method is valid
    if payment_id not in user.payment_methods:
        raise PolicyViolationException("Invalid payment method.")

    # Ensure the correct charge is applied for extra baggage
    expected_charge = expected_nonfree_baggages * 50
    if expected_charge > 0:
        # Check if the payment history reflects the correct charge
        total_paid = sum(payment.amount for payment in reservation.payment_history if payment.payment_id == payment_id)
        if total_paid < expected_charge:
            raise PolicyViolationException("Insufficient payment for extra baggage.")
        elif total_paid > expected_charge:
            raise PolicyViolationException("Overpayment detected for extra baggage.")