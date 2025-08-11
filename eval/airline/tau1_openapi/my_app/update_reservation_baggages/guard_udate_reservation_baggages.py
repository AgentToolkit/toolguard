from typing import Any, Dict

from my_app.common import ChatHistory, PolicyViolationException
from my_app.domain import FlightBookingApi, GetReservationDetailsParametersQuery, GetReservationDetailsResponse, GetUserDetailsParametersQuery, UpdateReservationBaggagesRequest

def guard_update_reservation_baggages(request:UpdateReservationBaggagesRequest, history: ChatHistory, api:FlightBookingApi):
    reservation = api.get_reservation_details(GetReservationDetailsParametersQuery(reservation_id=request.reservation_id))

    # check_user_confirmed(history, api)
    check_no_bag_removed(reservation, request, api)
    check_payment_method(reservation, request, api)


# def check_user_confirmed(history:ChatHistory, api:FlightBookingApi):
#     confirmed = history.ask_bool("Has the user provided explicit confirmation to proceed with updating the reservation?")
#     if not confirmed:
#         raise PolicyViolationException("GetUserDetailsResponse has not provided explicit confirmation to proceed with updating the reservation.")
    
def check_no_bag_removed(reservation:GetReservationDetailsResponse, request: UpdateReservationBaggagesRequest, api:FlightBookingApi):
    current_total_baggages = reservation.total_baggages
    assert current_total_baggages
    if request.total_baggages < current_total_baggages:
        raise PolicyViolationException("Policy violation: Cannot remove checked bags, only additions are allowed.")
    
def check_payment_method(reservation:GetReservationDetailsResponse, request: UpdateReservationBaggagesRequest, api:FlightBookingApi):
    if not request.payment_id:
        raise PolicyViolationException("Payment id was not specified") 
    user = api.get_user_details(
        GetUserDetailsParametersQuery(user_id=reservation.user_id)
    )
    if request.payment_id not in user.payment_methods:
        raise PolicyViolationException("All payment methods must be in the user's profile.")
