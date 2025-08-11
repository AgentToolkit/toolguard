from typing import *
import airline
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_obtain_payment_method_for_flight_changes(history: ChatHistory, api: I_Airline, reservation_id: str, cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], payment_id: str):
    """
    Policy to check: When updating a flight reservation using the UpdateReservationFlights tool, the agent must ensure that a valid payment method, either a gift card or a credit card stored in the user's profile, is provided for any additional costs or refunds associated with the change.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'.
        cabin: The cabin class of the reservation
        flights: An array of objects containing details about each piece of flight in the ENTIRE new reservation. Even if the a flight segment is not changed, it should still be included in the array.
        payment_id: The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'.
    """
    # Fetch user details to verify payment method
    try:
        user_details = api.get_user_details(reservation_id)
    except ValueError:
        raise PolicyViolationException("User details could not be retrieved.")

    if not user_details:
        raise PolicyViolationException("User details could not be retrieved.")

    # Check if the payment method is stored in the user's profile
    if payment_id not in user_details.payment_methods:
        raise PolicyViolationException("Payment method is not stored in the user's profile.")

    # Ensure the payment method is either a gift card or a credit card
    payment_method = user_details.payment_methods[payment_id]
    if payment_method.source not in ['gift_card', 'credit_card']:
        raise PolicyViolationException("Invalid payment method. Must be a gift card or credit card.")

    # Check if flights are being changed
    reservation_details = api.get_reservation_details(reservation_id)
    if reservation_details.flights != flights:
        raise PolicyViolationException("Flights have been changed, ensure a valid payment method is provided.")

    # Ensure a valid payment method is provided for any additional costs or refunds
    if payment_method.source == 'gift_card' and payment_method.amount <= 0:
        raise PolicyViolationException("Gift card balance is not enough for additional costs.")

    if payment_method.source == 'credit_card' and not payment_method.last_four:
        raise PolicyViolationException("Credit card information is incomplete.")