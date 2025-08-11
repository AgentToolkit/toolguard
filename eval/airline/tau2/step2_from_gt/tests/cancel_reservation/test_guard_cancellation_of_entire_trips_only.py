from unittest.mock import MagicMock, patch
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.cancel_reservation.guard_cancellation_of_entire_trips_only import guard_cancellation_of_entire_trips_only
from airline.i_airline import *
from datetime import datetime, timedelta

class TestGuardCancellationOfEntireTripsOnly:

    def test_compliance_all_segments_scheduled(self):
        """
        Policy: "Before using the CancelReservation tool, the agent should confirm that the entire trip is unused."
        Example: "An agent receives a user request for cancellation and checks each flight segment to ensure none have been flown or taken off."
        """
        
        # Mock the history service
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock the API
        api = MagicMock(spec=I_Airline)
        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="user123",
            origin="JFK",
            destination="LAX",
            flight_type="round_trip",
            cabin="economy",
            flights=[ReservationFlight(flight_number="AA123", origin="JFK", destination="LAX", date="2024-05-01", price=300)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None
        api.get_flight_status.side_effect = lambda flight_number, date: "scheduled" if flight_number == "AA123" and date == "2024-05-01" else "unknown"

        # Invoke function under test
        guard_cancellation_of_entire_trips_only(history, api, "ZFA04Y")

    def test_violation_segment_flying(self):
        """
        Policy: "If any flight segment has already been flown, the reservation cannot be canceled by the agent."
        Example: "The agent receives a request to cancel a trip, and while one of the segments shows a 'flying' status, the agent proceeds with CancelReservation."
        """
        
        # Mock the history service
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock the API
        api = MagicMock(spec=I_Airline)
        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="user123",
            origin="JFK",
            destination="LAX",
            flight_type="round_trip",
            cabin="economy",
            flights=[ReservationFlight(flight_number="AA123", origin="JFK", destination="LAX", date="2024-05-01", price=300)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None
        api.get_flight_status.side_effect = lambda flight_number, date: "flying" if flight_number == "AA123" and date == "2024-05-01" else "unknown"

        # Invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_cancellation_of_entire_trips_only(history, api, "ZFA04Y")

    def test_violation_segment_departed(self):
        """
        Policy: "If any flight segment has already been flown, the reservation cannot be canceled by the agent."
        Example: "An agent cancels a reservation marking all segments as 'scheduled' without confirming their status."
        """
        
        # Mock the history service
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock the API
        api = MagicMock(spec=I_Airline)
        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="user123",
            origin="JFK",
            destination="LAX",
            flight_type="round_trip",
            cabin="economy",
            flights=[ReservationFlight(flight_number="AA123", origin="JFK", destination="LAX", date="2024-05-01", price=300)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None
        api.get_flight_status.side_effect = lambda flight_number, date: "departed" if flight_number == "AA123" and date == "2024-05-01" else "unknown"

        # Invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_cancellation_of_entire_trips_only(history, api, "ZFA04Y")
