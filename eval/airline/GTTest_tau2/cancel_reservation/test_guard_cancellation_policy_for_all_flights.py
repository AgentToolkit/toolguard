from unittest.mock import MagicMock, patch
import pytest
from datetime import datetime, timedelta
from rt_toolguard.data_types import PolicyViolationException
from airline.cancel_reservation.guard_cancellation_policy_for_all_flights import guard_cancellation_policy_for_all_flights
from airline.i_airline import *

class TestGuardCancellationPolicyForAllFlights:

    def test_cancellation_within_24_hours(self):
        # Policy: "An agent checks and confirms the reservation was made within 24 hours before invoking CancelReservation."
        # Compliance example: "A user requests the cancellation of an economy class reservation booked 18 hours ago."
        
        # Mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock the API:
        reservation = Reservation.model_construct(
            reservation_id="ZFA04Y",
            user_id="user123",
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight.model_construct(flight_number="HAT001", date="2024-05-01", price=200)],
            passengers=[Passenger.model_construct(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[],
            created_at=(datetime.now() - timedelta(hours=18)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None

        # Invoke function under test.
        guard_cancellation_policy_for_all_flights(history, api, "ZFA04Y")

    def test_violation_no_insurance_economy_class(self):
        # Policy: "A user contacts support to cancel a reservation for an economy class ticket without having purchased travel insurance, and the booking was made more than 24 hours ago, yet the agent proceeds with cancellation."
        # Violation example: "A basic user requests a reservation cancellation 48 hours after purchase, without the airline canceling any flights, and the agent mistakenly processes the cancellation, violating the 24-hour window requirement for non-business class tickets."
        
        # Mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = False

        # Mock the API:
        reservation = Reservation.model_construct(
            reservation_id="ZFA04Y",
            user_id="user123",
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight.model_construct(flight_number="HAT001", date="2024-05-01", price=200)],
            passengers=[Passenger.model_construct(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[],
            created_at=(datetime.now() - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None

        # Invoke function under test.
        with pytest.raises(PolicyViolationException):
            guard_cancellation_policy_for_all_flights(history, api, "ZFA04Y")
