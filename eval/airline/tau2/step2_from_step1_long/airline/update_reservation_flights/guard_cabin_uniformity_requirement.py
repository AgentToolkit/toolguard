from typing import *
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_cabin_uniformity_requirement(history: ChatHistory, api: I_Airline, reservation_id: str, cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], payment_id: str):
    """
    Policy: Cabin class must be the same across all flights in a reservation.
    This guard enforces that all flights in the reservation update have the same cabin class, and that no partial update is performed.

    Args:
        history (ChatHistory): Chat history object (not used here).
        api (I_Airline): Airline API interface.
        reservation_id (str): The reservation ID.
        cabin (Literal): The cabin class for the update.
        flights (list): List of flights for the update.
        payment_id (str): Payment method ID (not used here).
    Raises:
        PolicyViolationException: If the cabin class is not uniform across all flights, or if a partial update is attempted.
    """
    # Fetch the current reservation details
    current_reservation = api.get_reservation_details(reservation_id)

    # Check that all flights are being updated (no partial update)
    if len(flights) != len(current_reservation.flights):
        raise PolicyViolationException("All flights in the reservation must be updated together. Partial update is not allowed.")

    # Check that the provided 'cabin' argument is valid
    if cabin not in ['business', 'economy', 'basic_economy']:
        raise PolicyViolationException(f"Invalid cabin class: {cabin}. Must be one of 'business', 'economy', or 'basic_economy'.")

    # Check that all flights in the update have the same cabin class
    for flight in flights:
        # If the flight is a dict and has a 'cabin' key, it must match the provided 'cabin' argument
        if isinstance(flight, dict):
            if 'cabin' in flight and flight['cabin'] != cabin:
                raise PolicyViolationException("Cabin class must be the same across all flights in the reservation.")
        # If the flight is a FlightInfo, check if it has a 'cabin' attribute
        elif hasattr(flight, 'cabin'):
            if getattr(flight, 'cabin') != cabin:
                raise PolicyViolationException("Cabin class must be the same across all flights in the reservation.")

    # Check that all flights in the update have the SAME cabin class among themselves
    # (defensive: if any flight has a different cabin than the others, raise)
    cabins_in_update = set()
    for flight in flights:
        if isinstance(flight, dict) and 'cabin' in flight:
            cabins_in_update.add(flight['cabin'])
        elif hasattr(flight, 'cabin'):
            cabins_in_update.add(getattr(flight, 'cabin'))
        else:
            cabins_in_update.add(cabin)  # If no cabin info, assume the provided cabin
    if len(cabins_in_update) > 1:
        raise PolicyViolationException("Cabin class must be the same across all flights in the reservation.")

    # Check that the current reservation does not already have mixed cabin classes
    cabins_in_current = set()
    for res_flight in current_reservation.flights:
        if hasattr(res_flight, 'cabin'):
            cabins_in_current.add(getattr(res_flight, 'cabin'))
        elif isinstance(res_flight, dict) and 'cabin' in res_flight:
            cabins_in_current.add(res_flight['cabin'])
    if len(cabins_in_current) > 1:
        raise PolicyViolationException("Current reservation has mixed cabin classes, which is not allowed.")

    # If all checks pass, the update is allowed
