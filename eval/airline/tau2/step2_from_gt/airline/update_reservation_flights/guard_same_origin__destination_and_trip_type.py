from typing import *
import airline
from rt_toolguard.data_types import ChatHistory
from airline.airline_types import *
from airline.i_airline import I_Airline

class PolicyViolationException(Exception):
    pass

def guard_same_origin__destination_and_trip_type(history: ChatHistory, api: I_Airline, reservation_id: str, cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], payment_id: str):
    """
    Policy to check: non-basic-economy reservation can be modified without changing the origin, destination, and trip type. Some flight segments can be kept, but their prices will not be updated based on the current price.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'.
        cabin: The cabin class of the reservation
        flights: An array of objects containing details about each piece of flight in the ENTIRE new reservation. Even if the a flight segment is not changed, it should still be included in the array.
        payment_id: The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'.
    """
    # Fetch the current reservation details
    reservation = api.get_reservation_details(reservation_id)

    # Check if the cabin is not basic economy
    if cabin != 'basic_economy':
        # Extract the original origin, destination, and trip type
        original_origin = reservation.origin
        original_destination = reservation.destination
        original_trip_type = reservation.flight_type

        # Extract the new origin, destination, and trip type from the flights
        new_origin = flights[0]['origin'] if isinstance(flights[0], dict) else flights[0].origin
        new_destination = flights[-1]['destination'] if isinstance(flights[-1], dict) else flights[-1].destination
        new_trip_type = 'round_trip' if len(flights) > 1 else 'one_way'

        # Validate that the origin, destination, and trip type have not changed
        if original_origin != new_origin:
            raise PolicyViolationException("Origin cannot be changed for non-basic-economy reservations.")
        if original_destination != new_destination:
            raise PolicyViolationException("Destination cannot be changed for non-basic-economy reservations.")
        if original_trip_type != new_trip_type:
            raise PolicyViolationException("Trip type cannot be changed for non-basic-economy reservations.")