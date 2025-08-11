from typing import *
import airline
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_keep_the_same_origin_and_destination(history: ChatHistory, api: I_Airline, reservation_id: str, cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], payment_id: str):
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
        # Validate that the origin and destination remain unchanged
        first_flight = flights[0]
        flight_info = first_flight if isinstance(first_flight, FlightInfo) else FlightInfo(**first_flight)
        the_flight = api.get_scheduled_flight(flight_number=flight_info.flight_number)
        if the_flight.origin != reservation.origin:
            raise PolicyViolationException("Origin cannot be changed for non-basic-economy reservations.")
    
        if reservation.flight_type == "one_way":
            last_flight = flights[-1]
            flight_info = last_flight if isinstance(last_flight, FlightInfo) else FlightInfo(**last_flight)
            the_flight = api.get_scheduled_flight(flight_number=flight_info.flight_number)
            if the_flight.destination != reservation.destination:
                raise PolicyViolationException("Destination cannot be changed for non-basic-economy reservations.")

        # Validate that the trip type remains unchanged
        # if reservation.flight_type != 'one_way' and reservation.flight_type != 'round_trip':
        #     raise PolicyViolationException("Trip type cannot be changed for non-basic-economy reservations.")

    # Note: Prices are not updated based on the current price, hence no check is needed for price updates.