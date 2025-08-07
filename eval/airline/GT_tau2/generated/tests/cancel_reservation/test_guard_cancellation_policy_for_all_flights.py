from unittest.mock import MagicMock, patch
import pytest
from datetime import datetime, timedelta
from rt_toolguard.data_types import PolicyViolationException
from airline.cancel_reservation.guard_cancellation_policy_for_all_flights import guard_cancellation_policy_for_all_flights
from airline.i_airline import *
from airline.airline_types import *


def test_cancellation_within_24_hours():
    """
    Policy: "The cancellation is within 24 hours of booking"
    Example: "An agent checks and confirms the reservation was made within 24 hours before invoking CancelReservation."
    """
    
    # Mock the history service
    history = MagicMock()
    history.ask_bool.return_value = True

    # Mock the API
    reservation = Reservation(
        reservation_id="ZFA04Y",
        user_id="user123",
        origin="JFK",
        destination="LAX",
        flight_type="one_way",
        cabin="economy",
        flights=[ReservationFlight(flight_number="HAT001", origin="JFK", destination="LAX", date="2024-05-01", price=300)],
        passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
        payment_history=[Payment(payment_id="pay123", amount=300)],
        created_at=(datetime.now() - timedelta(hours=23)).strftime("%Y-%m-%dT%H:%M:%S"),
        total_baggages=1,
        nonfree_baggages=0,
        insurance="no",
        status=None
    )

    api = MagicMock(spec=I_Airline)
    api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None

    # Invoke function under test
    guard_cancellation_policy_for_all_flights(history, api, "ZFA04Y")


def test_cancellation_without_insurance_economy_class():
    """
    Policy: "For economy class, cancellation is only allowed if travel insurance was purchased and qualifies"
    Example: "A user contacts support to cancel a reservation for an economy class ticket without having purchased travel insurance, and the booking was made more than 24 hours ago."
    """
    
    # Mock the history service
    history = MagicMock()
    history.ask_bool.return_value = True

    # Mock the API
    reservation = Reservation(
        reservation_id="ZFA04Y",
        user_id="user123",
        origin="JFK",
        destination="LAX",
        flight_type="one_way",
        cabin="economy",
        flights=[ReservationFlight(flight_number="HAT001", origin="JFK", destination="LAX", date="2024-05-01", price=300)],
        passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
        payment_history=[Payment(payment_id="pay123", amount=300)],
        created_at=(datetime.now() - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%S"),
        total_baggages=1,
        nonfree_baggages=0,
        insurance="no",
        status=None
    )

    api = MagicMock(spec=I_Airline)
    api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None

    # Invoke function under test
    with pytest.raises(PolicyViolationException):
        guard_cancellation_policy_for_all_flights(history, api, "ZFA04Y")
