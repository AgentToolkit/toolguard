from typing import *
import airline
from rt_toolguard.data_types import ChatHistory
from airline.airline_types import *
from airline.i_airline import I_Airline

from airline.transfer_to_human_agents.guard_transfer_to_human_agent_conditions import guard_transfer_to_human_agent_conditions
from airline.transfer_to_human_agents.guard_flight_segment_transfer_condition import guard_flight_segment_transfer_condition
from airline.transfer_to_human_agents.guard_human_agent_assistance_limitation import guard_human_agent_assistance_limitation


def guard_transfer_to_human_agents(history: ChatHistory, api: I_Airline, summary: str):
    """
    Checks that a tool call complies to the policies.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        summary: A summary of the user's issue.
         
    """
    
    guard_transfer_to_human_agent_conditions(history, api, summary)
    guard_flight_segment_transfer_condition(history, api, summary)
    guard_human_agent_assistance_limitation(history, api, summary)
