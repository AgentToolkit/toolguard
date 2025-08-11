from typing import *
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_transfer_requirement_for_human_assistance(history: ChatHistory, api: I_Airline, reservation_id: str, passengers: list[Passenger | dict]):
    """
    Policy to check: Agents are instructed to transfer users to a human agent when passenger modification requests surpass the capabilities of the 'update_reservation_passengers' tool. This includes any change in passenger count or modifications not supported by the tool. Agents must confirm that all available tools have been used and that the issue cannot be resolved due to passenger number constraints before initiating the transfer.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'.
        passengers: An array of objects containing details about each passenger.
    """
    # Get the current reservation details
    reservation = api.get_reservation_details(reservation_id)
    current_passenger_count = len(reservation.passengers)
    new_passenger_count = len(passengers)

    # Policy: Any change in passenger count is NOT allowed by update_reservation_passengers
    if new_passenger_count != current_passenger_count:
        raise PolicyViolationException(
            "Passenger count change detected. Must transfer to human agent as per policy."
        )
    # Note: If further checks for unsupported modifications are required, add them here.
    # For now, only passenger count change is explicitly forbidden by the tool and policy.
