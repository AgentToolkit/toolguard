from typing import *
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_flight_segment_transfer_condition(history: ChatHistory, api: I_Airline, summary: str):
    """
    Policy to check: If a user requests to cancel a trip and any segments have already been flown, transfer the user to a human agent as the current tool cannot process partial trip cancellations.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        summary: A summary of the user's issue.
    
    Raises:
        PolicyViolationException: If any segment in the reservation has already been flown.
    """
    import re
    # Extract reservation_id from summary using regex
    reservation_id_match = re.search(r'reservation id\s*[:#]?\s*([A-Z0-9]{6,})', summary, re.IGNORECASE)
    reservation_id = None
    if reservation_id_match:
        reservation_id = reservation_id_match.group(1)
    if not reservation_id:
        # If reservation_id cannot be determined, we cannot validate
        return
    try:
        reservation = api.get_reservation_details(reservation_id)
    except Exception:
        # If reservation not found, skip check
        return
    # Check each flight segment in the reservation
    for flight in reservation.flights:
        flight_number = flight.flight_number
        date = flight.date
        try:
            status = api.get_flight_status(flight_number, date)
        except Exception:
            continue  # If flight not found, skip this segment
        # If any segment is flown, flying, or cancelled, raise PolicyViolationException
        if status in ['landed', 'flying', 'cancelled']:
            # Policy: Cannot process cancellation if any segment is flown, flying, or cancelled
            raise PolicyViolationException(
                "Cannot process cancellation: at least one segment has already been flown, is in progress, or cancelled. Transfer to human agent required per policy.")
    # If all segments are not flown, no violation
    # Policy: If no segment is flown, flying, or cancelled, allow automated cancellation
