from typing import *
import airline
from rt_toolguard.data_types import ChatHistory
from airline.airline_types import *
from airline.i_airline import I_Airline

# from airline.book_reservation.guard_user_confirmation_before_database_update import guard_user_confirmation_before_database_update
from airline.book_reservation.guard_flight_passenger_limit_for_booking import guard_flight_passenger_limit_for_booking
from airline.book_reservation.guard_payment_method_limits_in_booking import guard_payment_method_limits_in_booking
from airline.book_reservation.guard_user_id_requirement_for_flight_booking import guard_user_id_requirement_for_flight_booking
from airline.book_reservation.guard_prohibition_on_modifying_user_s_passenger_count import guard_prohibition_on_modifying_user_s_passenger_count


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
    
    # guard_user_confirmation_before_database_update(history, api, user_id, origin, destination, flight_type, cabin, flights, passengers, payment_methods, total_baggages, nonfree_baggages, insurance)
    guard_flight_passenger_limit_for_booking(history, api, user_id, origin, destination, flight_type, cabin, flights, passengers, payment_methods, total_baggages, nonfree_baggages, insurance)
    guard_payment_method_limits_in_booking(history, api, user_id, origin, destination, flight_type, cabin, flights, passengers, payment_methods, total_baggages, nonfree_baggages, insurance)
    guard_user_id_requirement_for_flight_booking(history, api, user_id, origin, destination, flight_type, cabin, flights, passengers, payment_methods, total_baggages, nonfree_baggages, insurance)
    guard_prohibition_on_modifying_user_s_passenger_count(history, api, user_id, origin, destination, flight_type, cabin, flights, passengers, payment_methods, total_baggages, nonfree_baggages, insurance)
