from typing import *
import airline
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_payment_method_restriction(history: ChatHistory, api: I_Airline, user_id: str, origin: str, destination: str, flight_type: Literal['round_trip', 'one_way'], cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], passengers: list[Passenger | dict], payment_methods: list[Payment | dict], total_baggages: int, nonfree_baggages: int, insurance: Literal['yes', 'no']):
    """
    Policy to check: Ensure each reservation through BookReservation uses a maximum of one travel certificate, one credit card, and up to three gift cards. Verify that all payment methods are pre-registered in the user profile before proceeding with booking to maintain security and database integrity.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        user_id: The ID of the user to book the reservation such as 'sara_doe_496'.
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
    # Retrieve user details to check pre-registered payment methods
    user_details = api.get_user_details(user_id)
    registered_payment_methods = user_details.payment_methods

    # Counters for different payment methods
    credit_card_count = 0
    gift_card_count = 0
    certificate_count = 0

    # Check each payment method
    for payment in payment_methods:
        if isinstance(payment, dict):
            payment = Payment(**payment)

        # Check if payment method is registered
        if payment.payment_id not in registered_payment_methods:
            raise PolicyViolationException(f"Payment method {payment.payment_id} is not registered in the user's profile.")

        payment_method = registered_payment_methods[payment.payment_id]
        # Count the types of payment methods
        if isinstance(payment_method, CreditCard):
            credit_card_count += 1
        elif isinstance(payment_method, GiftCard):
            gift_card_count += 1
        elif isinstance(payment_method, Certificate):
            certificate_count += 1

    # Validate the counts against policy
    if credit_card_count > 1:
        raise PolicyViolationException("More than one credit card is not allowed.")
    if gift_card_count > 3:
        raise PolicyViolationException("More than three gift cards are not allowed.")
    if certificate_count > 1:
        raise PolicyViolationException("More than one travel certificate is not allowed.")