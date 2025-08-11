from typing import *
import airline
from rt_toolguard.data_types import ChatHistory
from airline.airline_types import *
from airline.i_airline import I_Airline

from airline.update_reservation_flights.guard_explicit_user_confirmation_required import guard_explicit_user_confirmation_required
from airline.update_reservation_flights.guard_cannot_modify_basic_economy_flights import guard_cannot_modify_basic_economy_flights
from airline.update_reservation_flights.guard_cabin_change_payment_requirement import guard_cabin_change_payment_requirement
from airline.update_reservation_flights.guard_cabin_uniformity_requirement import guard_cabin_uniformity_requirement
from airline.update_reservation_flights.guard_payment_method_requirement_for_flight_changes import guard_payment_method_requirement_for_flight_changes
from airline.update_reservation_flights.guard_flight_modification_api_limitation_check import guard_flight_modification_api_limitation_check
from airline.update_reservation_flights.guard_consistency_across_flight_segments import guard_consistency_across_flight_segments


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
    
    guard_explicit_user_confirmation_required(history, api, reservation_id, cabin, flights, payment_id)
    guard_cannot_modify_basic_economy_flights(history, api, reservation_id, cabin, flights, payment_id)
    guard_cabin_change_payment_requirement(history, api, reservation_id, cabin, flights, payment_id)
    guard_cabin_uniformity_requirement(history, api, reservation_id, cabin, flights, payment_id)
    guard_payment_method_requirement_for_flight_changes(history, api, reservation_id, cabin, flights, payment_id)
    guard_flight_modification_api_limitation_check(history, api, reservation_id, cabin, flights, payment_id)
    guard_consistency_across_flight_segments(history, api, reservation_id, cabin, flights, payment_id)
