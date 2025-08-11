from typing import *
import airline
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline


def guard_seats_are_available(history: ChatHistory, api: I_Airline, user_id: str, origin: str, destination: str, flight_type: Literal['round_trip', 'one_way'], cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], passengers: list[Passenger | dict], payment_methods: list[Payment | dict], total_baggages: int, nonfree_baggages: int, insurance: Literal['yes', 'no']):
    """
    Policy to check: Flights chosen for booking must have enough available seats for all passengers, and prices listed for booking.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        user_id: The ID of the user to book the reservation such as 'sara_doe_496'.
        origin: The IATA code for the origin city such as 'SFO'.
        destination: The IATA code for the destination city such as 'JFK'.
        flight_type: The type of flight such as 'one_way' or 'round_trip'.
        cabin: The cabin class such as 'basic_economy', 'economy', or 'business'.
        flights: An array of objects containing details about each piece of flight.
        passengers: An array of objects containing details about each passenger.
        payment_methods: An array of objects containing details about each payment method.
        total_baggages: The total number of baggage items to book the reservation.
        nonfree_baggages: The number of non-free baggage items to book the reservation.
        insurance: Whether the reservation has insurance.
    """
    num_passengers = len(passengers)

    for flight in flights:
        # Ensure flight is a FlightInfo object
        if isinstance(flight, dict):
            flight = FlightInfo(**flight)

        # Get flight instance details
        flight_instance = api.get_flight_instance(flight.flight_number, flight.date)

        # Check if the flight is available
        if flight_instance.status != 'available':
            raise PolicyViolationException(f"Flight {flight.flight_number} on {flight.date} is not available.")

        # Check if there are enough available seats in the specified cabin
        available_seats = flight_instance.available_seats.get(cabin, 0)
        if available_seats < num_passengers:
            raise PolicyViolationException(f"Not enough available seats in {cabin} class for flight {flight.flight_number} on {flight.date}.")

        # Check if prices are listed for the specified cabin
        if cabin not in flight_instance.prices:
            raise PolicyViolationException(f"Prices not listed for {cabin} class for flight {flight.flight_number} on {flight.date}.")