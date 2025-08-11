from typing import *
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_strict_cancellation_rules_enforcement(history: ChatHistory, api: I_Airline, reservation_id: str):
    """
    Enforces strict cancellation rules before allowing reservation cancellation.
    Checks:
    - Reservation must be cancelled by the airline, OR
    - Reservation must be within 24 hours of booking, OR
    - Travel insurance applies due to health or weather (for basic/economy), OR
    - Business flights can always be cancelled if unused.
    - Partial cancellations are prohibited (all segments must be unused).
    If none of these are met, transfer to human agent is required.
    Raises PolicyViolationException if policy is violated.
    """
    # Get reservation details
    try:
        reservation = api.get_reservation_details(reservation_id)
    except Exception as e:
        raise PolicyViolationException(f"Reservation not found: {e}")

    # Check if reservation is already cancelled
    if reservation.status == 'cancelled':
        raise PolicyViolationException("Reservation is already cancelled.")

    # Check if any flight segment has already been flown (partial cancellation prohibited)
    for flight in reservation.flights:
        flight_status = api.get_flight_instance(flight.flight_number, flight.date)
        if getattr(flight_status, 'status', None) in ['landed', 'flying']:
            raise PolicyViolationException("Partial cancellations are prohibited. Some segments have already been flown.")

    # Check if any flight was cancelled by the airline
    airline_cancelled = any(getattr(api.get_flight_instance(flight.flight_number, flight.date), 'status', None) == 'cancelled' for flight in reservation.flights)
    if airline_cancelled:
        return  # Allowed to cancel

    # Check if reservation is within 24 hours of booking
    from datetime import datetime, timedelta
    try:
        created_at = datetime.strptime(reservation.created_at, "%Y-%m-%dT%H:%M:%S")
    except Exception:
        raise PolicyViolationException("Invalid reservation creation timestamp.")
    if datetime.utcnow() - created_at <= timedelta(hours=24):
        return  # Allowed to cancel

    # Check travel insurance for basic/economy flights
    if reservation.cabin in ['basic_economy', 'economy']:
        if reservation.insurance == 'yes':
            # Health or weather condition must apply (ask history)
            if history.ask_bool("Is the cancellation due to health or weather conditions?"):
                return  # Allowed to cancel
            else:
                raise PolicyViolationException("Travel insurance cancellation only allowed for health or weather reasons.")
        else:
            raise PolicyViolationException("Basic/economy flights require travel insurance for cancellation after 24 hours.")

    # Business flights: can always be cancelled if unused
    if reservation.cabin == 'business':
        return  # Allowed to cancel

    # If none of the above, transfer to human agent required
    raise PolicyViolationException("Cancellation not allowed by policy. Please transfer to a human agent.")
