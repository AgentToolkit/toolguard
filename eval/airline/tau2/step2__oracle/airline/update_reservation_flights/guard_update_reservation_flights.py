from typing import *
import airline
from airline.update_reservation_flights.guard_basic_economy_flights_cannot_be_modified import guard_basic_economy_flights_cannot_be_modified
from airline.update_reservation_flights.guard_keep_the_same_origin_and_destination import guard_keep_the_same_origin_and_destination
from rt_toolguard.data_types import ChatHistory
from airline.airline_types import *
from airline.i_airline import I_Airline

from airline.update_reservation_flights.guard_flight_status_restrictions import guard_flight_status_restrictions
from airline.update_reservation_flights.guard_seats_are_available import guard_seats_are_available
from airline.update_reservation_flights.guard_obtain_payment_method_for_flight_changes import guard_obtain_payment_method_for_flight_changes


def guard_update_reservation_flights(history: ChatHistory, api: I_Airline, reservation_id: str, cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], payment_id: str):
    """
    Checks that a tool call complies to the policies.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'.
        cabin: The cabin class of the reservation
        flights: An array of objects containing details about each piece of flight in the ENTIRE new reservation. Even if the a flight segment is not changed, it should still be included in the array.
        payment_id: The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'.
         
    """
    
    guard_flight_status_restrictions(history, api, reservation_id, cabin, flights, payment_id)
    guard_seats_are_available(history, api, reservation_id, cabin, flights, payment_id)
    guard_obtain_payment_method_for_flight_changes(history, api, reservation_id, cabin, flights, payment_id)
    guard_keep_the_same_origin_and_destination(history, api, reservation_id, cabin, flights, payment_id)
    guard_basic_economy_flights_cannot_be_modified(history, api, reservation_id, cabin, flights, payment_id)
