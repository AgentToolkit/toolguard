from typing import *
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_user_id_requirement_for_flight_booking(history: ChatHistory, api: I_Airline, user_id: str, origin: str, destination: str, flight_type: Literal['round_trip', 'one_way'], cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], passengers: list[Passenger | dict], payment_methods: list[Payment | dict], total_baggages: int, nonfree_baggages: int, insurance: Literal['yes', 'no']):
    """
    Policy to check: The agent must first obtain the user ID before proceeding with flight booking and subsequent inquiries for trip type, origin, and destination.

    This guard ensures that the user_id is present and valid before allowing booking or any related inquiries.
    If user_id is missing or empty, a PolicyViolationException is raised.
    """
    # Check that user_id is provided and is a non-empty string
    if not user_id or not isinstance(user_id, str) or user_id.strip() == "":
        raise PolicyViolationException("User ID must be obtained before proceeding with flight booking or related inquiries.")
    # Optionally, check that the user_id exists in the backend
    try:
        api.get_user_details(user_id)
    except Exception:
        raise PolicyViolationException(f"User ID '{user_id}' is not valid or does not exist.")
