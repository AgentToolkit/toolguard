from typing import *
import airline
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_ensure_user_confirmation(history: ChatHistory, api: I_Airline, reservation_id: str, passengers: list[Passenger | dict]):
    """
    Policy to check: Before using ToolX to update passenger information in the booking database, an airline agent must present the details of the changes to the user and obtain explicit confirmation ('yes') from them before proceeding.

    This guard checks that explicit user confirmation ('yes') was obtained before updating passenger information for a reservation.
    It uses the chat history to verify confirmation and raises PolicyViolationException if confirmation is missing.

    Args:
        history (ChatHistory): Provides question-answer services over the past chat messages.
        api (I_Airline): API to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'.
        passengers: An array of objects containing details about each passenger.
    """
    # Ask the chat history if the user explicitly confirmed the passenger information update
    confirmed = history.ask_bool(
        f"Did the user explicitly confirm ('yes') the proposed passenger information update for reservation '{reservation_id}'?")
    if not confirmed:
        raise PolicyViolationException(
            "Explicit user confirmation ('yes') for passenger information update was not obtained.")
