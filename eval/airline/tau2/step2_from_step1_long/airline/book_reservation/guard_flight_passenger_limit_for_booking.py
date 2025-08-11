from typing import *
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_flight_passenger_limit_for_booking(history: ChatHistory, api: I_Airline, user_id: str, origin: str, destination: str, flight_type: Literal['round_trip', 'one_way'], cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], passengers: list[Passenger | dict], payment_methods: list[Payment | dict], total_baggages: int, nonfree_baggages: int, insurance: Literal['yes', 'no']):
    """
    Policy to check: A flight reservation can have at most five passengers, and all must fly the same flights in the same cabin.
    - Limit to five passengers per reservation.
    - All passengers must have first name, last name, and date of birth.
    - All passengers must share the same flight itinerary, cabin, and flight type.
    """
    # Check passenger count
    if len(passengers) > 5:
        raise PolicyViolationException("A flight reservation can have at most five passengers.")

    # Helper to extract flight key
    def flight_list_key(f):
        if isinstance(f, dict):
            return (f.get('flight_number'), f.get('date'))
        else:
            return (getattr(f, 'flight_number', None), getattr(f, 'date', None))
    reservation_flights_set = set([flight_list_key(f) for f in flights])

    # Check each passenger
    for idx, p in enumerate(passengers):
        # Accept both dict and Passenger
        if isinstance(p, dict):
            first_name = p.get('first_name')
            last_name = p.get('last_name')
            dob = p.get('dob')
            passenger_flights = p.get('flights')
            passenger_cabin = p.get('cabin')
            passenger_flight_type = p.get('flight_type')
        else:
            first_name = getattr(p, 'first_name', None)
            last_name = getattr(p, 'last_name', None)
            dob = getattr(p, 'dob', None)
            passenger_flights = getattr(p, 'flights', None)
            passenger_cabin = getattr(p, 'cabin', None)
            passenger_flight_type = getattr(p, 'flight_type', None)
        # Check required details
        if not first_name or not last_name or not dob:
            raise PolicyViolationException(f"Passenger {idx+1} is missing required details (first name, last name, or date of birth).")
        # Check flight itinerary
        if passenger_flights is not None:
            passenger_flights_set = set([flight_list_key(f) for f in passenger_flights])
            if passenger_flights_set != reservation_flights_set:
                raise PolicyViolationException(f"Passenger {idx+1} does not share the same flight itinerary as the reservation.")
        # Check cabin
        if passenger_cabin is not None and passenger_cabin != cabin:
            raise PolicyViolationException(f"Passenger {idx+1} does not have the same cabin class as the reservation.")
        # Check flight type
        if passenger_flight_type is not None and passenger_flight_type != flight_type:
            raise PolicyViolationException(f"Passenger {idx+1} does not have the same flight type as the reservation.")
    # Additionally, check that all passengers are assigned to all flights in the reservation if per-passenger flights are specified
    # This covers the case where a passenger is missing a segment
    for idx, p in enumerate(passengers):
        passenger_flights = None
        if isinstance(p, dict):
            passenger_flights = p.get('flights')
        else:
            passenger_flights = getattr(p, 'flights', None)
        if passenger_flights is not None:
            passenger_flights_set = set([flight_list_key(f) for f in passenger_flights])
            if passenger_flights_set != reservation_flights_set:
                raise PolicyViolationException(f"Passenger {idx+1} must be assigned to all flights in the reservation.")
        # Check cabin for all passengers
        if isinstance(p, dict):
            passenger_cabin = p.get('cabin')
        else:
            passenger_cabin = getattr(p, 'cabin', None)
        if passenger_cabin is not None and passenger_cabin != cabin:
            raise PolicyViolationException(f"Passenger {idx+1} does not have the same cabin class as the reservation.")
        # Check flight type for all passengers
        if isinstance(p, dict):
            passenger_flight_type = p.get('flight_type')
        else:
            passenger_flight_type = getattr(p, 'flight_type', None)
        if passenger_flight_type is not None and passenger_flight_type != flight_type:
            raise PolicyViolationException(f"Passenger {idx+1} does not have the same flight type as the reservation.")
    # All policy checks passed
    return
