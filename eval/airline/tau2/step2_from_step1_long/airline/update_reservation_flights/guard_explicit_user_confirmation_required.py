from typing import *
import airline
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_explicit_user_confirmation_required(history: ChatHistory, api: I_Airline, reservation_id: str, cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], payment_id: str):
    """
    Policy to check: Before using ToolX for reservation updates including flights, baggage, cabin class, or passenger information, ensure you present all action details to the user in a clear manner and receive their explicit confirmation (yes) to proceed. Compliance cannot be pre-validated by ToolX; it requires interaction history to confirm user consent.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'.
        cabin: The cabin class of the reservation
        flights: An array of objects containing details about each piece of flight in the ENTIRE new reservation. Even if the a flight segment is not changed, it should still be included in the array.
        payment_id: The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'.
    
    Returns:
        None. Raises PolicyViolationException if explicit user confirmation is not found in history.
    """
    # Ask the history if explicit confirmation ('yes') was given by the user after presenting all action details
    # This is required by policy and cannot be pre-validated by ToolX
    # Only explicit 'yes' is accepted, not implicit consent
    confirmed = history.ask_bool(
        "Did the user explicitly say 'yes' to confirm the presented reservation update details (including flights, baggage, cabin class, or passenger information)? Only explicit 'yes' is valid."
    )
    if not confirmed:
        raise PolicyViolationException(
            "Explicit user confirmation ('yes') is required before updating reservation details. No valid confirmation found in chat history."
        )
