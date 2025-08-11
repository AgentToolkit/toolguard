from typing import Any, Dict, List

from datetime import datetime, timedelta

from my_app.common import ChatHistory, PolicyViolationException
from my_app.domain import CancelReservationRequest, FlightBookingApi, GetFlightInstanceParametersQuery, GetFlightInstanceResponse, GetReservationDetailsParametersQuery, GetReservationDetailsResponse
CUR_TIME = datetime.now()
def time_since(date_str:str)->timedelta:
    return CUR_TIME - datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")

def guard_cancel_reservation(req: CancelReservationRequest, history: ChatHistory, api:FlightBookingApi):
    if not req.reservation_id:
        raise PolicyViolationException("Missing reservation ID.")

    reservation = api.get_reservation_details(GetReservationDetailsParametersQuery(reservation_id=req.reservation_id))
    flights = [api.get_flight_instance(
        GetFlightInstanceParametersQuery(flight_id=fl.flight_number, date=fl.date))
        for fl in reservation.flights or []]

    check_cancellation_condition(reservation, flights, history, api)
    check_flight_segments_not_flown(reservation, flights, history, api)
    # check_user_explictly_confirmed(reservation, flights, history, api)
    
def check_cancellation_condition(reservation:GetReservationDetailsResponse, flights:List[GetFlightInstanceResponse], history: ChatHistory, api:FlightBookingApi):
    assert reservation.created_at
    if time_since(reservation.created_at) > timedelta(hours=24):
        # Check if the flight is not cancelled by the airline and conditions are met
        travel_insurance = reservation.insurance
        cabin = reservation.cabin
        if not ((any([fl.status == "cancelled" for fl in flights])) or 
                (cabin == "business") or 
                (travel_insurance == "yes" and history.ask_bool("Look at the reason the user provided for cancelling the reservation. Can the reason be classified as one of: [\"health\", \"weather\"]?"))
            ):
            raise PolicyViolationException("The reservation cannot be canceled based on the current conditions.")

def check_flight_segments_not_flown(reservation:GetReservationDetailsResponse, flights:List[GetFlightInstanceResponse], history: ChatHistory, api:FlightBookingApi):
    # Check if any segment of the trip is already used
    for flight in flights:
        if flight.status in ["landed", "flying"]:
            raise PolicyViolationException("Some segments of the trip have already been flown.")
        
# def check_user_explictly_confirmed(reservation:GetReservationDetailsResponse, flights:List[GetFlightInstanceResponse], history:ChatHistory, api:FlightBookingApi):
#     # Ensure user confirmation for cancellation
#     if not history.ask_bool("Did the user explicitly confirm the cancellation?"):
#         raise PolicyViolationException("GetUserDetailsResponse has not explicitly confirmed the cancellation.")