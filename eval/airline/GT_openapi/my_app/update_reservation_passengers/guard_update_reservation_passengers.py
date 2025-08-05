from typing import Any, Dict

from my_app.common import ChatHistory, PolicyViolationException
from my_app.domain import FlightBookingApi, GetReservationDetailsParametersQuery, UpdateReservationPassengersRequest

def guard_update_reservation_passengers(request:
    UpdateReservationPassengersRequest, history: ChatHistory, api:FlightBookingApi):
    
    check_same_num_passengers(request, history, api)
    # check_user_confirmed(history, api)


def check_same_num_passengers(request: UpdateReservationPassengersRequest, history: ChatHistory, api:FlightBookingApi):
    # Retrieve the current reservation details to compare number of passengers
    reservation = api.get_reservation_details(
        GetReservationDetailsParametersQuery(reservation_id=request.reservation_id)
    )

    # Policy check: The number of passengers should not change
    if len(request.passengers) != len(reservation.passengers or []):
        raise PolicyViolationException("The number of passengers cannot be modified.")

# def check_user_confirmed(history: ChatHistory, api:FlightBookingApi):
#     confirmed = history.ask_bool("Determine if the user explicitly confirmed the action to update passenger information.")
#     if not confirmed:
#         raise PolicyViolationException("Explicit user confirmation to update passenger information was not obtained.")
