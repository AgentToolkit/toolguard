from typing import *
from datetime import datetime, timedelta
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline


def guard_cancellation_policy_for_all_flights(history: ChatHistory, api: I_Airline, reservation_id: str):
    """
    Policy to check: To use the 'cancel_reservation' tool, confirm the following with the user: 
    1) The cancellation is within 24 hours of booking, 
    2) The airline cancelled the flight, 
    3) For economy class, cancellation is only allowed if travel insurance was purchased and qualifies, 
    4) Business class flights can be cancelled anytime. 
    These conditions must be validated prior to invoking the tool.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'.
    """
    # Fetch reservation details
    reservation = api.get_reservation_details(reservation_id)
    
    # Check if the reservation was made within 24 hours
    reservation_time = datetime.strptime(reservation.created_at, "%Y-%m-%dT%H:%M:%S")
    if datetime.now() - reservation_time <= timedelta(hours=24):
        return  # Cancellation is allowed within 24 hours

    # Check if the airline cancelled the flight
    for flight in reservation.flights:
        flight_status = api.get_flight_status(flight.flight_number, flight.date)
        if flight_status == 'cancelled':
            return  # Cancellation is allowed if the airline cancelled the flight

    # Check cabin class and insurance for economy class
    if reservation.cabin in ['economy', 'basic_economy']:
        if reservation.insurance == 'yes':
            return  # Cancellation is allowed if insurance was purchased
        else:
            raise PolicyViolationException("Economy class cancellation requires travel insurance.")

    # Business class can be cancelled anytime
    if reservation.cabin == 'business':
        return

    # If none of the conditions are met, raise an exception
    raise PolicyViolationException("Cancellation policy conditions not met.")