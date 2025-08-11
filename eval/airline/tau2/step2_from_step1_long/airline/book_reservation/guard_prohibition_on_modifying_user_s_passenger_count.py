from typing import *
import airline
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_prohibition_on_modifying_user_s_passenger_count(history: ChatHistory, api: I_Airline, user_id: str, origin: str, destination: str, flight_type: Literal['round_trip', 'one_way'], cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], passengers: list[Passenger | dict], payment_methods: list[Payment | dict], total_baggages: int, nonfree_baggages: int, insurance: Literal['yes', 'no']):
    """
    Policy to check: The agent must not alter the number of passengers in a reservation once established, though modifications to passenger details like name or date of birth are allowed.

    This guard checks that the number of passengers in the current modification matches the number of passengers in the original reservation. If the count is changed, a PolicyViolationException is raised.
    Only the passenger details (such as name, dob, preferences) may be updated, not the count.
    """
    # Retrieve the user's reservations
    user_details = api.get_user_details(user_id)
    # Find the matching reservation by origin, destination, flight_type, cabin
    for res_id in user_details.reservations:
        reservation = api.get_reservation_details(res_id)
        if (reservation.origin == origin and reservation.destination == destination and
            reservation.flight_type == flight_type and reservation.cabin == cabin):
            # Compare flights by flight_number and date
            if len(reservation.flights) == len(flights):
                flights_match = True
                for rf, f in zip(reservation.flights, flights):
                    f_number = f['flight_number'] if isinstance(f, dict) else f.flight_number
                    f_date = f['date'] if isinstance(f, dict) else f.date
                    if rf.flight_number != f_number or rf.date != f_date:
                        flights_match = False
                        break
                if flights_match:
                    # Check passenger count
                    if len(passengers) != len(reservation.passengers):
                        raise PolicyViolationException("Modifying the number of passengers in a reservation is prohibited.")
                    # If passenger count matches, allow modification of passenger details
                    return  # Policy satisfied
    # If no matching reservation is found, DO raise PolicyViolationException, as the policy prohibits changing passenger count for any established reservation
    # This covers cases where the reservation is being modified but does not match any existing reservation (e.g., count changed)
    raise PolicyViolationException("Modifying the number of passengers in a reservation is prohibited.")
