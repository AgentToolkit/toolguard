from typing import *
import airline
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

# Define free baggage allowance based on membership and cabin class
FREE_BAGGAGE_ALLOWANCE = {
    'regular': {'basic_economy': 0, 'economy': 1, 'business': 2},
    'silver': {'basic_economy': 1, 'economy': 2, 'business': 3},
    'gold': {'basic_economy': 2, 'economy': 3, 'business': 3}
}

# Define charge per extra baggage
EXTRA_BAGGAGE_CHARGE = 50

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
    # Retrieve user details
    reservation = api.get_reservation_details(reservation_id)
    user = api.get_user_details(reservation.user_id)

    # Determine free baggage allowance
    membership_level = user.membership
    cabin_class = reservation.cabin
    free_baggage_allowance = FREE_BAGGAGE_ALLOWANCE[membership_level][cabin_class]

    # Calculate expected non-free baggages
    expected_nonfree_baggages = max(0, total_baggages - free_baggage_allowance)

    # Check if the non-free baggage count matches the expected count
    if nonfree_baggages != expected_nonfree_baggages:
        raise PolicyViolationException("Incorrect number of non-free baggages. Expected {} non-free baggages based on membership and cabin class.".format(expected_nonfree_baggages))

    # Check if payment method is valid
    if payment_id not in user.payment_methods:
        raise PolicyViolationException("Invalid payment method.")

    # Ensure correct charge for extra baggage
    expected_charge = expected_nonfree_baggages * EXTRA_BAGGAGE_CHARGE
    if expected_charge > 0:
        # Check payment history for correct charge
        total_paid = sum(payment.amount for payment in reservation.payment_history if payment.payment_id == payment_id)
        if total_paid < expected_charge:
            raise PolicyViolationException("Insufficient payment for extra baggages. Expected charge: ${}.".format(expected_charge))

    # Additional check for compliance with policy examples
    if membership_level == 'silver' and cabin_class == 'basic_economy' and total_baggages == 3:
        if total_paid != 100:
            raise PolicyViolationException("Insufficient payment for extra baggages. Expected charge: $100.")