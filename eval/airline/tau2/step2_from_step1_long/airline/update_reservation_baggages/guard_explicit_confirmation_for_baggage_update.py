from typing import *
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_explicit_confirmation_for_baggage_update(history: ChatHistory, api: I_Airline, reservation_id: str, total_baggages: int, nonfree_baggages: int, payment_id: str):
    """
    Policy to check: Before invoking the 'update_reservation_baggages' tool to update baggage information in a reservation,
    ensure you list all changes and receive explicit user confirmation (yes) to proceed.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'
        total_baggages: The updated total number of baggage items included in the reservation.
        nonfree_baggages: The updated number of non-free baggage items included in the reservation.
        payment_id: The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'.
    Raises:
        PolicyViolationException: If explicit confirmation was not received or changes were not listed.
    """
    # Get current reservation details
    try:
        reservation = api.get_reservation_details(reservation_id)
    except Exception:
        # If reservation not found, let the tool itself handle this error
        return

    # Prepare a summary of changes
    changes = []
    if reservation.total_baggages != total_baggages:
        changes.append(f"total baggages: {reservation.total_baggages} -> {total_baggages}")
    if reservation.nonfree_baggages != nonfree_baggages:
        changes.append(f"nonfree baggages: {reservation.nonfree_baggages} -> {nonfree_baggages}")
    # Always include payment method
    changes.append(f"payment method: {payment_id}")

    # Check that changes were listed in the chat history
    if changes:
        changes_listed = history.ask_bool(
            f"Did the agent list the following baggage update changes for reservation '{reservation_id}': {', '.join(changes)}?"
        )
        if not changes_listed:
            raise PolicyViolationException("All changes must be listed before updating baggage information.")

    # Check for explicit user confirmation
    confirmed = history.ask_bool(
        f"Did the user explicitly confirm (yes) to proceed with updating baggage information for reservation '{reservation_id}'?"
    )
    if not confirmed:
        raise PolicyViolationException("Explicit user confirmation (yes) is required before updating baggage information.")
