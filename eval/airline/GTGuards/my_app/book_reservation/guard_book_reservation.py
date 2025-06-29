
from typing import Any, Dict

from my_app.common import ChatHistory, PolicyViolationException
from my_app.domain import BookReservationRequest, FlightBookingApi, GetFlightInstanceParametersQuery, GetUserDetailsParametersQuery, GetUserDetailsResponse


def guard_book_reservation(req: BookReservationRequest, history: ChatHistory, api: FlightBookingApi):
    check_mandatory_args(req)

    user = api.get_user_details(GetUserDetailsParametersQuery(user_id=req.user_id))
    if not user:
        raise PolicyViolationException("GetUserDetailsResponse ID is invalid or does not exist.")
    
    check_passengers(req, user, history, api)
    check_payment_methods(req, user, history, api)
    check_baggages(req, user, history, api)
    check_flights_availability(req, user, history, api)
    check_iata_airports(req, api)
    # check_explicit_user_confirmation(req, user, history, api)

def check_mandatory_args(req: BookReservationRequest):
    if(not req.user_id):
        raise PolicyViolationException("A reservation must have a user_id")
    if(not req.flight_type):
        raise PolicyViolationException("A reservation must have a flight_type")
    if(not req.origin):
        raise PolicyViolationException("A reservation must have a origin")
    if(not req.destination):
        raise PolicyViolationException("A reservation must have a destination")
    if(not req.passengers):
        raise PolicyViolationException("A reservation must have a passengers")
    if(not req.payment_methods):
        raise PolicyViolationException("A reservation must have a payment_methods")

def check_iata_airports(req:BookReservationRequest, api:FlightBookingApi):
    airports = api.list_all_airports().root
    if req.origin not in airports:
        raise PolicyViolationException("Origin airport is not a iata airport")
    if req.destination not in airports:
        raise PolicyViolationException("Destination airport is not a iata airport")

def check_passengers(req: BookReservationRequest, user: GetUserDetailsResponse, history: ChatHistory, api: FlightBookingApi):
    if len(req.passengers) > 5:
        raise PolicyViolationException("A reservation can have at most 5 passengers.")
    
    for p in req.passengers:
        if not p.first_name:
            raise PolicyViolationException("Each passenger must have a first name.")
        if not p.last_name:
            raise PolicyViolationException("Each passenger must have a last name.")
        if not p.dob:
            raise PolicyViolationException("Each passenger must have a date of birth.")

def check_baggages(req:BookReservationRequest, user: GetUserDetailsResponse, history: ChatHistory, api: FlightBookingApi):
    # Validate baggage allowance
    membership = user.membership
    assert membership
    free_baggages_per_passanger = {
        "regular": {"basic_economy": 0, "economy": 1, "business": 2},
        "silver": {"basic_economy": 1, "economy": 2, "business": 3},
        "gold": {"basic_economy": 2, "economy": 3, "business": 3},
    }
    allowed_free_per_passanger = free_baggages_per_passanger.get(membership, {}).get(req.cabin, 0)
    if req.nonfree_baggages > req.total_baggages:
        raise PolicyViolationException("Nonfree baggages cannot exceed total baggages.")
    
    total_allowed_free = allowed_free_per_passanger * len(req.passengers)
    baggages_to_pay = max(req.total_baggages - total_allowed_free, 0)
    if baggages_to_pay > req.nonfree_baggages:
        raise PolicyViolationException("GetUserDetailsResponse is being undercharged for baggages.")
    if baggages_to_pay < req.nonfree_baggages:
        raise PolicyViolationException("GetUserDetailsResponse is being overcharged for baggages.")

def check_payment_methods(req:BookReservationRequest, user: GetUserDetailsResponse, history: ChatHistory, api: FlightBookingApi):
    # Validate payment methods
    assert user.payment_methods
    if not all(pm.payment_id in user.payment_methods for pm in req.payment_methods):
        raise PolicyViolationException("All payment methods must be in the user's profile.")
    # if len(payment_methods) > 3:
    #     errors.append("At most 3 payment methods can be used (1 travel certificate, 1 credit card, 3 gift cards).")
    travel_certificate_count = sum(1 for method in req.payment_methods if 'certificate' in method.payment_id)
    if travel_certificate_count > 1:
        raise PolicyViolationException("Invalid payment methods: at most one travel certificate is allowed.")
    
    credit_card_count = sum(1 for method in req.payment_methods if 'credit_card' in method.payment_id)
    if credit_card_count > 1:
        raise PolicyViolationException("Invalid payment methods: at most one credit card is allowed.")
    
    gift_card_count = sum(1 for method in req.payment_methods if 'gift_card' in method.payment_id)
    if gift_card_count > 3:
        raise PolicyViolationException("Invalid payment methods: at most three gift cards are allowed.")

def check_flights_availability(req: BookReservationRequest, user: GetUserDetailsResponse, history: ChatHistory, api: FlightBookingApi):
    # Validate flight availability
    for flight in req.flights:
        flight_instance = api.get_flight_instance(
            GetFlightInstanceParametersQuery(flight_id=flight.flight_number, date=flight.date)
        )
        if not flight_instance:
            raise PolicyViolationException(f"Flight {flight.flight_number} is unavailable.")

        if flight_instance.status != "available":
            raise PolicyViolationException(f"Flight {flight.flight_number} is unavailable.")
        
        avail_seats = getattr(flight_instance.available_seats, req.cabin)
        if avail_seats < len(req.passengers):
            raise PolicyViolationException(f"There are only {avail_seats} available seats in {req.cabin} cabin.")

# def check_explicit_user_confirmation(req: BookReservationRequest, user: GetUserDetailsResponse, history: ChatHistory, api: FlightBookingApi):
#     # Check explicit confirmation from user
#     if not history.ask_bool("Has the user explicitly confirmed the booking details?"):
#         raise PolicyViolationException("GetUserDetailsResponse did not explicitly confirmed the booking.")
    