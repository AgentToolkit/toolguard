from typing import *
import airline
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
    # Verify that the user ID exists in the system
    try:
        user_details = api.get_user_details(user_id)
    except ValueError:
        raise PolicyViolationException("User ID does not exist in the system records.")

    # Ensure that the necessary booking information is gathered
    if not origin or not destination or not flight_type:
        raise PolicyViolationException("Missing necessary booking information: origin, destination, or flight type.")

    # Additional checks for user profile verification
    if not user_details:
        raise PolicyViolationException("User details could not be retrieved, verification failed.")

    # Check if the user ID is correctly obtained
    if user_id != user_details.user_id:
        raise PolicyViolationException("The obtained user ID does not match the system records.")

    # Ensure the user ID is verified before proceeding
    if not history.was_tool_called('get_user_details'):
        raise PolicyViolationException("User ID verification step was not performed.")

    # Check if the user ID was obtained from the chat history
    if not history.ask_bool(f"Was the user ID '{user_id}' obtained from the chat history?"):
        raise PolicyViolationException("User ID was not obtained from the chat history.")

    # Ensure the user ID is correctly obtained before invoking BookReservation
    if not user_details or user_id != user_details.user_id:
        raise PolicyViolationException("User ID is not correctly obtained before invoking BookReservation.")