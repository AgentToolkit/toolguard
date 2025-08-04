from typing import *
import airline
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_obtain_user_and_reservation_ids(history: ChatHistory, api: I_Airline, reservation_id: str, total_baggages: int, nonfree_baggages: int, payment_id: str):
    """
    Policy to check: The agent must first obtain the user id and the reservation id.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'
        total_baggages: The updated total number of baggage items included in the reservation.
        nonfree_baggages: The updated number of non-free baggage items included in the reservation.
        payment_id: The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'.
    """
    # Check if the user ID and reservation ID have been obtained
    user_id_obtained = history.was_tool_called("get_user_details")
    reservation_id_obtained = history.was_tool_called("get_reservation_details")

    # Ensure both user ID and reservation ID are obtained before proceeding
    if not user_id_obtained:
        raise PolicyViolationException("User ID has not been obtained.")
    if not reservation_id_obtained:
        raise PolicyViolationException("Reservation ID has not been obtained.")

    # Additional checks based on review comments
    if not (user_id_obtained and reservation_id_obtained):
        raise PolicyViolationException("Both User ID and Reservation ID must be obtained before proceeding.")

    # Ensure the reservation ID matches the obtained reservation details
    reservation_details = api.get_reservation_details(reservation_id)
    if reservation_details.reservation_id != reservation_id:
        raise PolicyViolationException("Provided reservation ID does not match obtained reservation details.")

    # Ensure the payment method is valid
    user_details = api.get_user_details(reservation_details.user_id)
    if payment_id not in user_details.payment_methods:
        raise PolicyViolationException("Invalid payment method provided.")