from typing import *
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_compensation_for_cancelled_or_delayed_flights(history: ChatHistory, api: I_Airline, user_id: str, amount: int):
    """
    Policy to check: Agents can issue compensation certificates using the `send_certificate` tool, but only for users who meet specific eligibility criteria: they must be silver/gold members, have travel insurance, or travel in business class. Compensation amounts are $100 per passenger for cancellations, and $50 per passenger for delays if the reservation is altered as requested by the user. Before sending compensation, the agent must ensure eligibility by verifying the user's membership, whether they have purchased travel insurance, the class they are flying, and the status of the flight.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        user_id: The ID of the user to book the reservation, such as 'sara_doe_496'.
        amount: The amount of the certificate to send.
    """
    # Step 1: Confirm user explicitly complained and requested compensation
    if not history.ask_bool("Did the user explicitly complain about a cancelled or delayed flight and request compensation?"):
        raise PolicyViolationException("User did not complain or request compensation.")

    # Step 2: Get user details
    user = api.get_user_details(user_id)
    membership = user.membership
    reservation_ids = user.reservations

    # Step 3: Find the most recent affected reservation (assume last one)
    if not reservation_ids:
        raise PolicyViolationException("No reservations found for user.")
    reservation = api.get_reservation_details(reservation_ids[-1])

    # Step 4: Check eligibility
    # Policy: Do not compensate if the user is regular member and has no travel insurance and flies (basic) economy.
    eligible = False
    if membership in ('gold', 'silver'):
        eligible = True
    if reservation.insurance == 'yes':
        eligible = True
    if reservation.cabin == 'business':
        eligible = True
    # If user is regular, no insurance, and not business class, not eligible
    if not eligible:
        raise PolicyViolationException("User is not eligible for compensation: must be silver/gold member, have insurance, or travel in business class.")

    # Step 5: Check flight status and compensation amount
    num_passengers = len(reservation.passengers)
    flights = reservation.flights
    cancelled = False
    delayed = False
    for flight in flights:
        status = api.get_flight_status(flight.flight_number, flight.date)
        if status == 'cancelled':
            cancelled = True
        if status == 'delayed':
            delayed = True
    # Step 6: Validate compensation amount and reservation alteration for delays
    if cancelled:
        expected_amount = 100 * num_passengers
        if amount != expected_amount:
            raise PolicyViolationException(f"Compensation for cancelled flights must be $100 per passenger. Expected: {expected_amount}, got: {amount}.")
    elif delayed:
        # Must confirm reservation was altered as requested by user
        if not history.ask_bool("Did the user request a reservation change or cancellation due to the delay, and was the reservation altered as requested?"):
            raise PolicyViolationException("Compensation for delayed flights requires reservation to be altered as requested by the user.")
        expected_amount = 50 * num_passengers
        if amount != expected_amount:
            raise PolicyViolationException(f"Compensation for delayed flights must be $50 per passenger. Expected: {expected_amount}, got: {amount}.")
    else:
        raise PolicyViolationException("No cancelled or delayed flights found in reservation.")

    # All checks passed
    return
