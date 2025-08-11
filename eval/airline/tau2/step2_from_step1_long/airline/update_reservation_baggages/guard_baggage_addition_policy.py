from typing import *
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_baggage_addition_policy(history: ChatHistory, api: I_Airline, reservation_id: str, total_baggages: int, nonfree_baggages: int, payment_id: str):
    """
    Enforces the Baggage Addition Policy for update_reservation_baggages:
    - Only allow adding checked bags, not removing.
    - Additional bags must be reflected in both total_baggages and nonfree_baggages.
    - Bag allowance is based on user's membership and cabin class.
    - Fees for extra bags must be calculated ($50 per extra bag).
    - Payment method must be stored in user's profile.
    """
    # Fetch current reservation details
    reservation = api.get_reservation_details(reservation_id)
    prev_total_baggages = reservation.total_baggages
    prev_nonfree_baggages = reservation.nonfree_baggages
    user_id = reservation.user_id
    cabin = reservation.cabin
    passengers = reservation.passengers

    # 1. Only allow adding bags, not removing
    if total_baggages < prev_total_baggages:
        raise PolicyViolationException("Cannot remove checked bags; only additions are allowed.")
    if nonfree_baggages < prev_nonfree_baggages:
        raise PolicyViolationException("Cannot reduce nonfree checked bags; only additions are allowed.")

    # 2. Get user details for membership and payment methods
    user = api.get_user_details(user_id)
    membership = user.membership
    payment_methods = user.payment_methods

    # 3. Check payment_id is in user's stored payment methods
    if payment_id not in payment_methods:
        raise PolicyViolationException("Payment method must be stored in user's profile.")

    # 4. Calculate free bag allowance per passenger
    # Policy table: membership x cabin
    allowance_table = {
        'regular': {'basic_economy': 0, 'economy': 1, 'business': 2},
        'silver':  {'basic_economy': 1, 'economy': 2, 'business': 3},
        'gold':    {'basic_economy': 2, 'economy': 3, 'business': 3},
    }
    free_bags = allowance_table[membership][cabin] * len(passengers)

    # 5. Check that total_baggages and nonfree_baggages are consistent
    #    - total_baggages must be >= free_bags
    #    - nonfree_baggages must be exactly (total_baggages - free_bags), but not less than zero
    #    - nonfree_baggages must not decrease
    expected_nonfree = max(total_baggages - free_bags, 0)
    if nonfree_baggages != expected_nonfree:
        raise PolicyViolationException(f"Nonfree bag count incorrect: expected {expected_nonfree} based on membership and cabin class.")
    if total_baggages < free_bags:
        raise PolicyViolationException(f"Total bag count cannot be less than free bag allowance ({free_bags}).")
    if nonfree_baggages < prev_nonfree_baggages:
        raise PolicyViolationException("Cannot reduce nonfree checked bags; only additions are allowed.")

    # 6. If there are additional nonfree bags, calculate fees
    added_nonfree = nonfree_baggages - prev_nonfree_baggages
    if added_nonfree > 0:
        expected_fee = 50 * added_nonfree
        # Optionally, you could check payment amount, but payment is processed by the tool itself
        # If you want to check payment history, you could do so here (not required by policy)

    # All checks passed
    return
