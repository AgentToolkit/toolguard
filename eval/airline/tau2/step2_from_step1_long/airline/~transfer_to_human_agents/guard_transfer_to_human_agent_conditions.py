from typing import *
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_transfer_to_human_agent_conditions(history: ChatHistory, api: I_Airline, summary: str):
    """
    Policy to check: Transfer a user to a human agent only if the user explicitly requests this transfer
    or if the problem cannot be resolved using available tools and policies within the scope of your actions.
    Include a summary of the user's issue when making the transfer.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        summary: A summary of the user's issue.
    """
    # Check if the user explicitly requested a human agent
    explicit_request = history.ask_bool(
        "Did the user explicitly request to be transferred to a human agent?"
    )
    if explicit_request:
        return  # Policy allows transfer if user explicitly requests

    # Check if the issue can be resolved using available tools
    # If any tool can resolve the issue, raise PolicyViolationException
    if history.ask_bool("Can the user's issue be resolved using the 'calculate' tool?"):
        raise PolicyViolationException("Transfer to human agent is not allowed: the issue can be resolved using the 'calculate' tool.")
    if history.ask_bool("Can the user's issue be resolved using the 'get_reservation_details' tool?"):
        raise PolicyViolationException("Transfer to human agent is not allowed: the issue can be resolved using the 'get_reservation_details' tool.")
    if history.ask_bool("Can the user's issue be resolved using the 'update_reservation_flights' tool?"):
        raise PolicyViolationException("Transfer to human agent is not allowed: the issue can be resolved using the 'update_reservation_flights' tool.")
    if history.ask_bool("Can the user's issue be resolved using the 'list_all_airports' tool?"):
        raise PolicyViolationException("Transfer to human agent is not allowed: the issue can be resolved using the 'list_all_airports' tool.")
    if history.ask_bool("Can the user's issue be resolved using the 'get_flight_status' tool?"):
        raise PolicyViolationException("Transfer to human agent is not allowed: the issue can be resolved using the 'get_flight_status' tool.")
    # If not explicitly requested and no tool can resolve, allow transfer
    return
