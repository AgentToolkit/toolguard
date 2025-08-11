from typing import *
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_flight_modification_api_limitation_check(history: ChatHistory, api: I_Airline, reservation_id: str, cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], payment_id: str):
    """
    Policy to check: Agents must verify the following before using the Flight Modification API:
    1. Basic economy flights are unmodifiable.
    2. For other flight reservations, ensure that origin, destination, and trip type remain unchanged from the initial booking.
    3. Prices for flight segments retained stay at original rates, not updated by the API. Manual validation of segment prices is required.
    """
    # Get the original reservation details
    reservation = api.get_reservation_details(reservation_id)

    # 1. Basic economy flights are unmodifiable
    if reservation.cabin == 'basic_economy':
        raise PolicyViolationException("Basic economy flights cannot be modified.")

    # 2. Ensure flights list is not empty
    if not flights:
        raise PolicyViolationException("Flights list cannot be empty.")

    # Helper to get flight attributes from FlightInfo or dict
    def get_flight_attr(flight, attr):
        if isinstance(flight, dict):
            return flight.get(attr)
        elif isinstance(flight, FlightInfo):
            if attr in ['flight_number', 'date']:
                return getattr(flight, attr)
            elif attr in ['origin', 'destination']:
                scheduled = api.get_scheduled_flight(flight.flight_number)
                return getattr(scheduled, attr)
            else:
                return None
        else:
            return None

    # Build a lookup for original flights (flight_number + date -> ReservationFlight)
    original_flights = {(f.flight_number, f.date): f for f in reservation.flights}

    # Policy: For origin/destination/trip type, compare only with original reservation flights
    # The origin of the first flight in the original reservation must match the origin of the first flight in the new flights
    # The destination of the last flight in the original reservation must match the destination of the last flight in the new flights
    # Trip type must remain unchanged
    # This allows for additional segments, as long as the endpoints and trip type are preserved
    def get_flight_origin(flight):
        return get_flight_attr(flight, 'origin')
    def get_flight_destination(flight):
        return get_flight_attr(flight, 'destination')

    # Get endpoints for original and new flights
    orig_first = reservation.flights[0]
    orig_last = reservation.flights[-1]
    new_first = flights[0]
    new_last = flights[-1]

    orig_origin = orig_first.origin
    orig_destination = orig_last.destination
    new_origin = get_flight_origin(new_first)
    new_destination = get_flight_destination(new_last)

    # Only check endpoints if the original flights list is not empty
    # If the new flights contain all original segments (by flight_number and date), endpoints are considered preserved
    # This allows for additional segments before/after, as long as the original endpoints are present in the same order
    # Find indices of original endpoints in the new flights
    orig_first_key = (orig_first.flight_number, orig_first.date)
    orig_last_key = (orig_last.flight_number, orig_last.date)
    new_keys = [(get_flight_attr(f, 'flight_number'), get_flight_attr(f, 'date')) for f in flights]
    try:
        first_idx = new_keys.index(orig_first_key)
        last_idx = new_keys.index(orig_last_key)
    except ValueError:
        raise PolicyViolationException("Original flight endpoints must be present in the new flights.")
    # Check that the endpoints match
    if get_flight_origin(flights[first_idx]) != orig_origin:
        raise PolicyViolationException("Origin must remain unchanged.")
    if get_flight_destination(flights[last_idx]) != orig_destination:
        raise PolicyViolationException("Destination must remain unchanged.")
    # Trip type check: round_trip must have two endpoints, one_way must have one
    if reservation.flight_type == 'one_way':
        # For one-way, endpoints must be preserved
        pass
    elif reservation.flight_type == 'round_trip':
        # For round-trip, endpoints must be origin -> destination, then destination -> origin
        # Find all segments that go from origin to destination, and from destination to origin
        # The first segment must be origin -> destination, last must be destination -> origin
        # Check that the first and last endpoints are correct
        if get_flight_origin(flights[first_idx]) != orig_origin or get_flight_destination(flights[first_idx]) != orig_destination:
            raise PolicyViolationException("Round-trip outbound flight must preserve original direction.")
        if get_flight_origin(flights[last_idx]) != orig_destination or get_flight_destination(flights[last_idx]) != orig_origin:
            raise PolicyViolationException("Round-trip inbound flight must preserve original direction.")
    else:
        raise PolicyViolationException("Unknown trip type in reservation.")

    # 3. Manual validation of segment prices for retained segments
    # For each new flight, if it matches an original flight (by flight_number and date), check price
    for flight in flights:
        flight_number = get_flight_attr(flight, 'flight_number')
        date = get_flight_attr(flight, 'date')
        if (flight_number, date) in original_flights:
            # Get current flight instance from API
            flight_instance = api.get_flight_instance(flight_number, date)
            # Only check price if the instance has 'prices' attribute and status == 'available'
            if hasattr(flight_instance, 'status') and flight_instance.status == 'available' and hasattr(flight_instance, 'prices'):
                original_price = original_flights[(flight_number, date)].price
                current_price = flight_instance.prices.get(reservation.cabin)
                if current_price != original_price:
                    raise PolicyViolationException(f"Price for flight {flight_number} on {date} does not match original rate. Manual validation required.")
    # All checks passed
    return
