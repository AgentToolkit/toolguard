from typing import *
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline


def guard_user_id_and_user_profile_verification(history: ChatHistory, api: I_Airline, user_id: str, origin: str, destination: str, flight_type: Literal['round_trip', 'one_way'], cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], passengers: list[Passenger | dict], payment_methods: list[Payment | dict], total_baggages: int, nonfree_baggages: int, insurance: Literal['yes', 'no']):
    """
    Policy to check: Before invoking ToolX (BookReservation), make sure that the user's ID is correctly obtained. After verifying the user ID, gather necessary booking information such as trip type, origin, and destination prior to making the reservation using ToolX.

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
    # Verify user ID exists in the system
    try:
        user_details = api.get_user_details(user_id)
    except ValueError:
        raise PolicyViolationException("User ID does not exist in the system.")

    # Ensure trip type, origin, and destination are provided
    if not flight_type or not origin or not destination:
        raise PolicyViolationException("Missing necessary booking information: trip type, origin, or destination.")

    # Additional checks can be added here if needed