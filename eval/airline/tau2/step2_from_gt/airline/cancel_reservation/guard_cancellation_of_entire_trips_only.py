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
    # Retrieve reservation details using the API
    reservation = api.get_reservation_details(reservation_id)

    # Check each flight segment in the reservation
    for flight in reservation.flights:
        # Get the status of each flight segment
        flight_status = api.get_flight_status(flight.flight_number, flight.date)

        # If any flight segment has already been flown, raise a PolicyViolationException
        if flight_status in ['landed', 'flying', 'departed']:
            raise PolicyViolationException("The reservation cannot be canceled as one or more flight segments have already been flown.")

        # Ensure all segments are confirmed as 'scheduled' or 'available'
        if flight_status not in ['scheduled', 'available', 'on time', 'delayed']:
            raise PolicyViolationException("The reservation cannot be canceled as one or more flight segments are not in a valid status for cancellation.")