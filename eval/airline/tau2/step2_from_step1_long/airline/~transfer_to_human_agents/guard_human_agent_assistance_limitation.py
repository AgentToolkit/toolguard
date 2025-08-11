from typing import *
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_human_agent_assistance_limitation(history: ChatHistory, api: I_Airline, summary: str):
    """
    Policy to check: For requests involving changes to the number of passengers in a reservation, notify the user that neither the automated system nor human agents can process this change. Therefore, transfer to a human agent is not permitted for these requests.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        summary: A summary of the user's issue.
    
    Raises:
        PolicyViolationException: If the request involves changing the number of passengers and attempts to transfer to a human agent.
    """
    # Keywords indicating a request to change the number of passengers
    passenger_count_keywords = [
        "change number of passengers", "add passenger", "remove passenger", "increase passengers", "decrease passengers",
        "modify passenger count", "update number of passengers", "change passenger count", "alter number of passengers",
        "add another passenger", "add additional passenger", "add more passengers", "reduce passengers", "subtract passenger"
    ]
    # Keywords indicating a request to transfer to a human agent
    transfer_keywords = [
        "transfer to human agent", "talk to human agent", "speak to human agent", "connect to human agent", "escalate to human agent",
        "transfer to agent", "talk to agent", "speak to agent", "connect to agent", "escalate to agent"
    ]
    summary_lower = summary.lower()
    # Check if the summary indicates a request to change the number of passengers
    involves_passenger_count_change = any(kw in summary_lower for kw in passenger_count_keywords)
    # Check if the summary indicates a transfer to human agent is being requested
    involves_transfer_to_agent = any(kw in summary_lower for kw in transfer_keywords)
    # Policy: If both are true, raise violation
    if involves_passenger_count_change and involves_transfer_to_agent:
        raise PolicyViolationException(
            "Transfer to human agent is not permitted for requests involving changes to the number of passengers in a reservation. Neither automated nor human agents can process this change."
        )
    # Additionally, if the summary only involves changing the number of passengers (even without explicit transfer request), raise violation
    if involves_passenger_count_change:
        raise PolicyViolationException(
            "Requests involving changes to the number of passengers in a reservation cannot be processed by either automated or human agents."
        )
    # If not, allow the request (no exception raised)
