from typing import *
import airline
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_flight_status_restrictions(history: ChatHistory, api: I_Airline, reservation_id: str, cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], payment_id: str):
    """
    Policy to check: Flights chosen for booking using ToolX must have the status 'available' to ensure that they have not taken off. Flights with status 'delayed', 'on time', or 'flying' cannot be booked.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'.
        cabin: The cabin class of the reservation
        flights: An array of objects containing details about each piece of flight in the ENTIRE new reservation. Even if the a flight segment is not changed, it should still be included in the array.
        payment_id: The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'.
    """
    for flight in flights:
        flight_number = flight['flight_number'] if isinstance(flight, dict) else flight.flight_number
        date = flight['date'] if isinstance(flight, dict) else flight.date
        status = api.get_flight_status(flight_number, date)
        if status not in ['available']:
            raise PolicyViolationException(f"Flight {flight_number} on {date} has status '{status}', which cannot be booked.")