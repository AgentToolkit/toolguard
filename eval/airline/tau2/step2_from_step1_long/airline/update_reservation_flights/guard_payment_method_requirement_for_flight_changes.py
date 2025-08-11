from typing import *
import airline
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_payment_method_requirement_for_flight_changes(history: ChatHistory, api: I_Airline, reservation_id: str, cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], payment_id: str):
    """
    Policy to check: Whenever flights in a reservation are changed, ensure the user provides one valid gift card or credit card from their profile as the payment or refund method. Without this, flight changes cannot be processed.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'.
        cabin: The cabin class of the reservation
        flights: An array of objects containing details about each piece of flight in the ENTIRE new reservation. Even if the a flight segment is not changed, it should still be included in the array.
        payment_id: The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'.
    Raises:
        PolicyViolationException: If the payment method is not a valid gift card or credit card from the user's profile.
    """
    # Get user_id from reservation
    reservation = api.get_reservation_details(reservation_id)
    user_id = reservation.user_id
    user = api.get_user_details(user_id)
    payment_methods = user.payment_methods

    # Check if payment_id is in user's payment_methods
    if payment_id not in payment_methods:
        raise PolicyViolationException("Payment method must be from user's profile.")
    method = payment_methods[payment_id]
    # Only allow gift card or credit card
    if getattr(method, 'source', None) not in ['gift_card', 'credit_card']:
        raise PolicyViolationException("Payment method must be a valid gift card or credit card from user's profile.")
    # If payment_id is valid and of correct type, pass
    # Otherwise, PolicyViolationException is raised above
