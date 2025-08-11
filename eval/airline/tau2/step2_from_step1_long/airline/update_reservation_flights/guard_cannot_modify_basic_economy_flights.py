from typing import *
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_cannot_modify_basic_economy_flights(history: ChatHistory, api: I_Airline, reservation_id: str, cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], payment_id: str):
    """
    Policy enforcement for update_reservation_flights:
    1. Basic economy flights in a reservation cannot be modified at all.
    2. For reservations that are not classified as basic economy, modifications are allowed but must not change the origin, destination, or trip type.
    This guard enforces both rules before allowing update_reservation_flights.
    """
    # Fetch the original reservation details
    reservation = api.get_reservation_details(reservation_id)

    # 1. If the reservation is basic economy, no modifications are allowed
    if reservation.cabin == 'basic_economy':
        raise PolicyViolationException("Basic economy flights cannot be modified.")

    # 2. For non-basic economy, origin, destination, and trip type must not change
    # Extract new origin, destination, and trip type from the flights and cabin arguments
    # The flights argument contains the full new itinerary
    # We assume all flights in the reservation have the same origin/destination as the original
    # For round_trip, there may be two flights (outbound/inbound), for one_way, one flight
    # We check that the new flights match the original reservation's origin/destination
    def get_flight_attr(flight, attr):
        # flight can be FlightInfo or dict
        if isinstance(flight, dict):
            return flight.get(attr)
        return getattr(flight, attr, None)

    # Check origin and destination for all flights
    for flight in flights:
        new_origin = get_flight_attr(flight, 'origin')
        new_destination = get_flight_attr(flight, 'destination')
        # If not present in FlightInfo, fallback to reservation
        if new_origin is not None and new_origin != reservation.origin:
            raise PolicyViolationException("Origin cannot be changed for non-basic economy reservations.")
        if new_destination is not None and new_destination != reservation.destination:
            raise PolicyViolationException("Destination cannot be changed for non-basic economy reservations.")

    # Check trip type
    # The trip type is not passed in the arguments, but the number of flights can indicate it
    # For round_trip: usually two flights (outbound/inbound), for one_way: one flight
    # We check that the new trip type matches the original reservation's trip type
    if reservation.flight_type == 'one_way':
        # Only allow if exactly one flight and origin/destination match
        if len(flights) != 1:
            raise PolicyViolationException("Trip type cannot be changed: one_way reservations must have exactly one flight.")
    elif reservation.flight_type == 'round_trip':
        # Only allow if exactly two flights and origin/destination match
        if len(flights) != 2:
            raise PolicyViolationException("Trip type cannot be changed: round_trip reservations must have exactly two flights.")
    else:
        # Unknown trip type, block modification
        raise PolicyViolationException("Unknown trip type in reservation.")

    # Check cabin class is not changed to or from basic_economy
    if cabin != reservation.cabin:
        # Only allow change if neither is basic_economy
        if cabin == 'basic_economy' or reservation.cabin == 'basic_economy':
            raise PolicyViolationException("Cabin class cannot be changed to or from basic_economy.")

    # All policy checks passed
    return
