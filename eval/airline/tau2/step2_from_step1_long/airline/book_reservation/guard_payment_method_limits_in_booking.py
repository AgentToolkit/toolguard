from typing import *
import airline
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_payment_method_limits_in_booking(history: ChatHistory, api: I_Airline, user_id: str, origin: str, destination: str, flight_type: Literal['round_trip', 'one_way'], cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], passengers: list[Passenger | dict], payment_methods: list[Payment | dict], total_baggages: int, nonfree_baggages: int, insurance: Literal['yes', 'no']):
    """
    Policy to check: Each reservation can use at most one travel certificate, one credit card, and three gift cards.
    All payment methods must already be in user profile for safety reasons.

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
    # Count payment method types
    certificate_count = 0
    credit_card_count = 0
    gift_card_count = 0
    payment_ids = set()
    for pm in payment_methods:
        # Accept both dict and Payment objects
        source = pm.get('source') if isinstance(pm, dict) else getattr(pm, 'source', None)
        payment_id = pm.get('id') if isinstance(pm, dict) else getattr(pm, 'payment_id', None)
        if source == 'certificate':
            certificate_count += 1
        elif source == 'credit_card':
            credit_card_count += 1
        elif source == 'gift_card':
            gift_card_count += 1
        # Collect payment ids for user profile check
        if payment_id:
            payment_ids.add(payment_id)
        else:
            # Try fallback for id field in GiftCard/Certificate/CreditCard
            fallback_id = pm.get('id') if isinstance(pm, dict) else getattr(pm, 'id', None)
            if fallback_id:
                payment_ids.add(fallback_id)
    # Policy checks
    if certificate_count > 1:
        raise PolicyViolationException("At most one travel certificate is allowed per reservation.")
    if credit_card_count > 1:
        raise PolicyViolationException("At most one credit card is allowed per reservation.")
    if gift_card_count > 3:
        raise PolicyViolationException("At most three gift cards are allowed per reservation.")
    # Check all payment methods are in user profile
    user = api.get_user_details(user_id)
    user_payment_ids = set(user.payment_methods.keys())
    if not payment_ids.issubset(user_payment_ids):
        raise PolicyViolationException("All payment methods must already be in user profile.")
