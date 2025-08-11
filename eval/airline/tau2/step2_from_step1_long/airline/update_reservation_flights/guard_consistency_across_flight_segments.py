from typing import *
import airline
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_consistency_across_flight_segments(history: ChatHistory, api: I_Airline, reservation_id: str, cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], payment_id: str):
    """
    Policy to check: When updating a reservation, all flight segments must be included in the list of flights provided, regardless of whether they have been altered or not.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'.
        cabin: The cabin class of the reservation
        flights: An array of objects containing details about each piece of flight in the ENTIRE new reservation. Even if a flight segment is not changed, it should still be included in the array.
        payment_id: The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'.
    Raises:
        PolicyViolationException: If not all original flight segments are included in the flights argument.
    """
    # Get the original reservation details
    reservation = api.get_reservation_details(reservation_id)
    original_segments = reservation.flights
    # Build a set of (flight_number, date) for original segments
    original_set = set((seg.flight_number, seg.date) for seg in original_segments)
    # Build a set of (flight_number, date) for provided flights
    provided_set = set()
    for f in flights:
        if isinstance(f, dict):
            flight_number = f.get('flight_number')
            date = f.get('date')
        else:
            flight_number = f.flight_number
            date = f.date
        provided_set.add((flight_number, date))
    # Check that all original segments are present in the provided flights
    if not original_set.issubset(provided_set):
        raise PolicyViolationException("All original flight segments must be included in the flights array, even if unchanged.")
