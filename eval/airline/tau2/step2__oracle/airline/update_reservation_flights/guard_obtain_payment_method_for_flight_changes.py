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
    # Retrieve reservation details to get the user ID
    try:
        reservation_details = api.get_reservation_details(reservation_id)
    except ValueError as e:
        raise PolicyViolationException(f"Error retrieving reservation details: {str(e)}")

    # Ensure reservation_details is not None
    if reservation_details is None:
        raise PolicyViolationException("Reservation details could not be retrieved.")

    # Retrieve user details to check stored payment methods
    try:
        user_details = api.get_user_details(reservation_details.user_id)
    except ValueError as e:
        raise PolicyViolationException(f"Error retrieving user details: {str(e)}")

    # Ensure user_details is not None
    if user_details is None:
        raise PolicyViolationException("User details could not be retrieved.")

    # Check if the payment method is stored in the user's profile
    if payment_id not in user_details.payment_methods:
        raise PolicyViolationException("The payment method is not stored in the user's profile.")

    # Check if the payment method is either a gift card or a credit card
    payment_method = user_details.payment_methods[payment_id]
    if payment_method.source not in ['credit_card', 'gift_card']:
        raise PolicyViolationException("The payment method must be a gift card or a credit card.")

    # Additional check for certificate usage
    if payment_method.source == 'certificate':
        raise PolicyViolationException("Certificates cannot be used for flight changes.")