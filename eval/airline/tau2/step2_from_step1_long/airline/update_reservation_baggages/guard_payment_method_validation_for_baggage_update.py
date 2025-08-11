from typing import *
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_payment_method_validation_for_baggage_update(history: ChatHistory, api: I_Airline, reservation_id: str, total_baggages: int, nonfree_baggages: int, payment_id: str):
    """
    Guard for payment method validation when updating baggages:
    - Only payment methods already stored in the user's profile may be used.
    - Each reservation can use at most one travel certificate, at most one credit card, and at most three gift cards for payment.
    - The payment_id must correspond to a payment method in the user's profile.
    """
    # Get reservation details to find the user_id
    reservation = api.get_reservation_details(reservation_id)
    user_id = reservation.user_id
    # Get user details to check payment methods
    user = api.get_user_details(user_id)
    payment_methods = user.payment_methods
    # Check that the payment_id is in the user's profile
    if payment_id not in payment_methods:
        raise PolicyViolationException("Payment method is not stored in user's profile.")
    # Count payment method types in payment_history for this reservation
    cert_count = 0
    cc_count = 0
    gc_count = 0
    # Check payment history for limits
    for payment in reservation.payment_history:
        pm_id = payment.payment_id
        if pm_id in payment_methods:
            pm = payment_methods[pm_id]
            if isinstance(pm, Certificate):
                cert_count += 1
            elif isinstance(pm, CreditCard):
                cc_count += 1
            elif isinstance(pm, GiftCard):
                gc_count += 1
    # Also count the current payment_id if it will be used for this update
    pm = payment_methods[payment_id]
    # Only count the payment_id if it is not already in payment_history
    already_used = any(payment.payment_id == payment_id for payment in reservation.payment_history)
    if not already_used:
        if isinstance(pm, Certificate):
            cert_count += 1
        elif isinstance(pm, CreditCard):
            cc_count += 1
        elif isinstance(pm, GiftCard):
            gc_count += 1
    # Enforce limits
    if cert_count > 1:
        raise PolicyViolationException("Cannot use more than one certificate per reservation.")
    if cc_count > 1:
        raise PolicyViolationException("Cannot use more than one credit card per reservation.")
    if gc_count > 3:
        raise PolicyViolationException("Cannot use more than three gift cards per reservation.")
    # Additionally, check if the current payment_id is a certificate, credit card, or gift card and if the limit is already reached
    if isinstance(pm, Certificate) and cert_count > 1:
        raise PolicyViolationException("Cannot use more than one certificate per reservation.")
    if isinstance(pm, CreditCard) and cc_count > 1:
        raise PolicyViolationException("Cannot use more than one credit card per reservation.")
    if isinstance(pm, GiftCard) and gc_count > 3:
        raise PolicyViolationException("Cannot use more than three gift cards per reservation.")
    # All checks passed
    return
