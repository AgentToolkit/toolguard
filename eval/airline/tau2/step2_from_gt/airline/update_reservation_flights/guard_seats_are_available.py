from typing import *
import airline
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_seats_are_available(history: ChatHistory, api: I_Airline, reservation_id: str, cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], payment_id: str):
    """
    Policy to check: Flights chosen for booking must have enough available seats for all passengers, and prices listed for booking.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'.
        cabin: The cabin class of the reservation
        flights: An array of objects containing details about each piece of flight in the ENTIRE new reservation. Even if the a flight segment is not changed, it should still be included in the array.
        payment_id: The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'.
    """
    reservation_details = api.get_reservation_details(reservation_id)
    num_passengers = len(reservation_details.passengers)

    for flight in flights:
        flight_number = flight['flight_number'] if isinstance(flight, dict) else flight.flight_number
        date = flight['date'] if isinstance(flight, dict) else flight.date
        flight_instance = api.get_flight_instance(flight_number, date)

        # Check if the flight is available
        if flight_instance.status != 'available':
            raise PolicyViolationException(f"Flight {flight_number} on {date} is not available for booking.")

        # Check if there are enough available seats in the specified cabin
        available_seats = flight_instance.available_seats.get(cabin, 0)
        if available_seats < num_passengers:
            raise PolicyViolationException(f"Not enough available seats in {cabin} class for flight {flight_number} on {date}. Required: {num_passengers}, Available: {available_seats}.")

        # Check if prices are listed for the specified cabin
        prices = flight_instance.prices.get(cabin)
        if prices is None:
            raise PolicyViolationException(f"Prices not listed for {cabin} class for flight {flight_number} on {date}.")