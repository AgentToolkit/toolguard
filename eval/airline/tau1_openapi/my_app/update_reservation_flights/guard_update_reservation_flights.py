from typing import Any, Dict

from my_app.common import ChatHistory, PolicyViolationException
from my_app.domain import FlightBookingApi, GetReservationDetailsParametersQuery, GetScheduledFlightParametersQuery, GetUserDetailsParametersQuery, UpdateReservationFlightsRequest

def guard_update_reservation_flights(request: UpdateReservationFlightsRequest, history: ChatHistory, api:FlightBookingApi):    
    check_not_bassic_economy(request, history, api)
    check_payment_method(request, history, api)
    check_flights(request, history, api)
    # check_user_confirmation(history, api)

def check_not_bassic_economy(req:UpdateReservationFlightsRequest, history:ChatHistory, api:FlightBookingApi):
    if req.cabin == "basic_economy":
        raise PolicyViolationException("Basic economy flights cannot be modified.")
    
def check_payment_method(req:UpdateReservationFlightsRequest, history:ChatHistory, api:FlightBookingApi):
    # Validate payment method
    if not req.payment_id:
        raise PolicyViolationException("Payment method is required for flight changes.")
    
    reservation = api.get_reservation_details(GetReservationDetailsParametersQuery(reservation_id=req.reservation_id))
    if not reservation:
        raise PolicyViolationException("Reservation ID not found")
    if not reservation.user_id:
        raise PolicyViolationException("Reservation user_id not found")
    user = api.get_user_details(
        GetUserDetailsParametersQuery(user_id=reservation.user_id)
    )
    if req.payment_id not in user.payment_methods:
        raise PolicyViolationException("All payment methods must be in the user's profile.")

    # #The user needs to provide one gift card or credit card for payment or refund method
    # if 'certificate' in req.payment_id:
    #     raise PolicyViolationException("The user can pay only using gift card or credit card")
    
def check_flights(req:UpdateReservationFlightsRequest, history:ChatHistory, api:FlightBookingApi):
    if not req.flights:
        raise PolicyViolationException("Cannot update a reservation that does not exist")
    
    old_reservation = api.get_reservation_details(
        GetReservationDetailsParametersQuery(reservation_id=req.reservation_id))
    if not old_reservation:
        raise PolicyViolationException("Cannot update a reservation that does not exist")
    
    flights = [api.get_scheduled_flight(
        GetScheduledFlightParametersQuery(flight_id = fl.flight_number))
        for fl in req.flights]
    if None in flights:
        raise PolicyViolationException("Referenced flight does not exist")
    
    if flights[0].origin != old_reservation.origin:
        raise PolicyViolationException("Origin cannot be modified")
    
    if old_reservation.flight_type == "one_way":
        if flights[-1].destination != old_reservation.destination:
            raise PolicyViolationException("Destination cannot be modified")
    else: #round trip
        if not any([fl.destination == old_reservation.destination for fl in flights]):
            raise PolicyViolationException("Destination cannot be modified")

# def check_user_confirmation(history:ChatHistory, api:FlightBookingApi):
#     confirmed = history.ask_bool("Determine if the user has explicitly confirmed the flight change.")
#     if not confirmed:
#         raise PolicyViolationException("GetUserDetailsResponse has not provided explicit confirmation for the flight change.")

