from typing import *
import airline
from rt_toolguard.data_types import ChatHistory
from airline.airline_types import *
from airline.i_airline import I_Airline

from airline.book_reservation.guard_user_id_and_user_profile_verification import guard_user_id_and_user_profile_verification
from airline.book_reservation.guard_flight_status_restrictions import guard_flight_status_restrictions
from airline.book_reservation.guard_seats_are_available import guard_seats_are_available
from airline.book_reservation.guard_passenger_information_completeness import guard_passenger_information_completeness
from airline.book_reservation.guard_payment_method_restriction import guard_payment_method_restriction
from airline.book_reservation.guard_checked_bag_allowance_by_membership_tier import guard_checked_bag_allowance_by_membership_tier


def guard_book_reservation(history: ChatHistory, api: I_Airline, user_id: str, origin: str, destination: str, flight_type: Literal['round_trip', 'one_way'], cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], passengers: list[Passenger | dict], payment_methods: list[Payment | dict], total_baggages: int, nonfree_baggages: int, insurance: Literal['yes', 'no']):
    """
    Checks that a tool call complies to the policies.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        user_id: The ID of the user to book the reservation such as 'sara_doe_496'`.
        origin: The IATA code for the origin city such as 'SFO'.
        destination: The IATA code for the destination city such as 'JFK'.
        flight_type: The type of flight such as 'one_way' or 'round_trip'.
        cabin: The cabin class such as 'basic_economy', 'economy', or 'business'.
        flights: An array of objects containing details about each piece of flight.
        passengers: An array of objects containing details about each passenger.
        payment_methods: An array of objects containing details about each payment method.
        total_baggages: The total number of baggage items to book the reservation.
        nonfree_baggages: The number of non-free baggage items to book the reservation.
        insurance: Whether the reservation has insurance. 
    """
    
    guard_user_id_and_user_profile_verification(history, api, user_id, origin, destination, flight_type, cabin, flights, passengers, payment_methods, total_baggages, nonfree_baggages, insurance)
    guard_flight_status_restrictions(history, api, user_id, origin, destination, flight_type, cabin, flights, passengers, payment_methods, total_baggages, nonfree_baggages, insurance)
    guard_seats_are_available(history, api, user_id, origin, destination, flight_type, cabin, flights, passengers, payment_methods, total_baggages, nonfree_baggages, insurance)
    guard_passenger_information_completeness(history, api, user_id, origin, destination, flight_type, cabin, flights, passengers, payment_methods, total_baggages, nonfree_baggages, insurance)
    guard_payment_method_restriction(history, api, user_id, origin, destination, flight_type, cabin, flights, passengers, payment_methods, total_baggages, nonfree_baggages, insurance)
    guard_checked_bag_allowance_by_membership_tier(history, api, user_id, origin, destination, flight_type, cabin, flights, passengers, payment_methods, total_baggages, nonfree_baggages, insurance)
