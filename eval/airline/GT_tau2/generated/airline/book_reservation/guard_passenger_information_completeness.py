from typing import *
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline


def guard_passenger_information_completeness(history: ChatHistory, api: I_Airline, user_id: str, origin: str, destination: str, flight_type: Literal['round_trip', 'one_way'], cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], passengers: list[Passenger | dict], payment_methods: list[Payment | dict], total_baggages: int, nonfree_baggages: int, insurance: Literal['yes', 'no']):
    """
    Policy to check: Ensure all required passenger details are collected. Limit to five passengers per reservation, with details including first name, last name, and date of birth.

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
    # Check if the number of passengers exceeds the limit
    if len(passengers) > 5:
        raise PolicyViolationException("More than five passengers are not allowed.")

    # Check if there are no passengers
    if len(passengers) == 0:
        raise PolicyViolationException("At least one passenger is required.")

    # Check for completeness of each passenger's information
    for passenger in passengers:
        if isinstance(passenger, dict):
            first_name = passenger.get('first_name')
            last_name = passenger.get('last_name')
            dob = passenger.get('dob')
        else:
            first_name = passenger.first_name
            last_name = passenger.last_name
            dob = passenger.dob

        if not first_name:
            raise PolicyViolationException("Passenger's first name is missing.")
        if not last_name:
            raise PolicyViolationException("Passenger's last name is missing.")
        if not dob:
            raise PolicyViolationException("Passenger's date of birth is missing.")