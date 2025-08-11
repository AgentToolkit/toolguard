from typing import *
import airline
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_cancellation_of_entire_trips_only(history: ChatHistory, api: I_Airline, reservation_id: str):
    """
    Policy to check: Before using the CancelReservation tool, the agent should confirm that the entire trip is unused. If any flight segment has already been flown, the reservation cannot be canceled by the agent and should be escalated to a human agent.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'.
    """
    try:
        reservation = api.get_reservation_details(reservation_id)
        for flight in reservation.flights:
            status = api.get_flight_status(flight.flight_number, flight.date)
            if status in ['flying', 'departed', 'landed']:
                raise PolicyViolationException("Flight segment has already been flown or is currently in progress.")
    except ValueError as e:
        raise PolicyViolationException(f"Error retrieving reservation details: {str(e)}")