from unittest.mock import MagicMock, patch
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.update_reservation_flights.guard_consistency_across_flight_segments import guard_consistency_across_flight_segments
from airline.airline_types import *
from airline.i_airline import *
from datetime import datetime, timedelta

class TestConsistencyAcrossFlightSegments:
    def test_update_with_all_segments_included(self):
        """
        Policy: "When updating a reservation, all flight segments must be included in the list of flights provided, regardless of whether they have been altered or not."
        Example: "A user's round-trip reservation is successfully updated with all flights listed, including the unchanged return flight segment, adhering to the policy requirement."
        """
        history = MagicMock()
        history.ask_bool.return_value = True
        api = MagicMock(spec=I_Airline)
        # Mock get_reservation_details to return a reservation with two segments
        reservation_id = "ZFA04Y"
        original_flights = [
            ReservationFlight(flight_number="HAT001", origin="SFO", destination="JFK", date="2024-07-01", price=300),
            ReservationFlight(flight_number="HAT002", origin="JFK", destination="SFO", date="2024-07-10", price=320)
        ]
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_123",
            origin="SFO",
            destination="JFK",
            flight_type="round_trip",
            cabin="economy",
            flights=original_flights,
            passengers=[Passenger(first_name="Sara", last_name="Doe", dob="1990-04-05")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=620)],
            created_at=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        flights_update = [
            FlightInfo(flight_number="HAT001", date="2024-07-01"),
            FlightInfo(flight_number="HAT002", date="2024-07-10")
        ]
        # Should not raise
        try:
            guard_consistency_across_flight_segments(history, api, reservation_id, "economy", flights_update, "credit_card_7815826")
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: expected no PolicyViolationException, but got: {e.message}")

    def test_update_with_only_altered_segment(self):
        """
        Policy: "When updating a reservation, all flight segments must be included in the list of flights provided, regardless of whether they have been altered or not."
        Example: "A user attempts to update their reservation but only includes the altered flight segment in the flights array, omitting the unchanged flight segments."
        """
        history = MagicMock()
        history.ask_bool.return_value = True
        api = MagicMock(spec=I_Airline)
        reservation_id = "ZFA04Y"
        original_flights = [
            ReservationFlight(flight_number="HAT001", origin="SFO", destination="JFK", date="2024-07-01", price=300),
            ReservationFlight(flight_number="HAT002", origin="JFK", destination="SFO", date="2024-07-10", price=320)
        ]
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_123",
            origin="SFO",
            destination="JFK",
            flight_type="round_trip",
            cabin="economy",
            flights=original_flights,
            passengers=[Passenger(first_name="Sara", last_name="Doe", dob="1990-04-05")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=620)],
            created_at=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        # Only altered segment included
        flights_update = [
            FlightInfo(flight_number="HAT001", date="2024-07-01")
        ]
        with pytest.raises(PolicyViolationException):
            guard_consistency_across_flight_segments(history, api, reservation_id, "economy", flights_update, "credit_card_7815826")

    def test_update_excludes_connecting_segments(self):
        """
        Policy: "When updating a reservation, all flight segments must be included in the list of flights provided, regardless of whether they have been altered or not."
        Example: "An agent updates the reservation for a flight change but mistakenly excludes connecting segments that were part of the same trip, leading to an incomplete submission."
        """
        history = MagicMock()
        history.ask_bool.return_value = True
        api = MagicMock(spec=I_Airline)
        reservation_id = "ZFA04Y"
        original_flights = [
            ReservationFlight(flight_number="HAT001", origin="SFO", destination="ORD", date="2024-07-01", price=200),
            ReservationFlight(flight_number="HAT002", origin="ORD", destination="JFK", date="2024-07-01", price=150),
            ReservationFlight(flight_number="HAT003", origin="JFK", destination="SFO", date="2024-07-10", price=320)
        ]
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_123",
            origin="SFO",
            destination="JFK",
            flight_type="round_trip",
            cabin="economy",
            flights=original_flights,
            passengers=[Passenger(first_name="Sara", last_name="Doe", dob="1990-04-05")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=670)],
            created_at=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        # Exclude connecting segment
        flights_update = [
            FlightInfo(flight_number="HAT001", date="2024-07-01"),
            FlightInfo(flight_number="HAT003", date="2024-07-10")
        ]
        with pytest.raises(PolicyViolationException):
            guard_consistency_across_flight_segments(history, api, reservation_id, "economy", flights_update, "credit_card_7815826")

    def test_update_only_new_cabin_segments(self):
        """
        Policy: "When updating a reservation, all flight segments must be included in the list of flights provided, regardless of whether they have been altered or not."
        Example: "During a reservation update involving a cabin class upgrade, the flights array only lists flights under the new cabin class, excluding previously booked ancillary services segments, violating the policy."
        """
        history = MagicMock()
        history.ask_bool.return_value = True
        api = MagicMock(spec=I_Airline)
        reservation_id = "ZFA04Y"
        original_flights = [
            ReservationFlight(flight_number="HAT001", origin="SFO", destination="JFK", date="2024-07-01", price=300),
            ReservationFlight(flight_number="HAT002", origin="JFK", destination="SFO", date="2024-07-10", price=320)
        ]
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_123",
            origin="SFO",
            destination="JFK",
            flight_type="round_trip",
            cabin="economy",
            flights=original_flights,
            passengers=[Passenger(first_name="Sara", last_name="Doe", dob="1990-04-05")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=620)],
            created_at=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        # Only flights under new cabin class included, ancillary segments excluded
        flights_update = [
            FlightInfo(flight_number="HAT001", date="2024-07-01")
        ]
        with pytest.raises(PolicyViolationException):
            guard_consistency_across_flight_segments(history, api, reservation_id, "business", flights_update, "credit_card_7815826")

    def test_update_all_segments_for_cabin_change(self):
        """
        Policy: "When updating a reservation, all flight segments must be included in the list of flights provided, regardless of whether they have been altered or not."
        Example: "A reservation update for altering the cabin class is processed correctly with all segments kept in the flights array to maintain consistency as per policy rules."
        """
        history = MagicMock()
        history.ask_bool.return_value = True
        api = MagicMock(spec=I_Airline)
        reservation_id = "ZFA04Y"
        original_flights = [
            ReservationFlight(flight_number="HAT001", origin="SFO", destination="JFK", date="2024-07-01", price=300),
            ReservationFlight(flight_number="HAT002", origin="JFK", destination="SFO", date="2024-07-10", price=320)
        ]
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_123",
            origin="SFO",
            destination="JFK",
            flight_type="round_trip",
            cabin="economy",
            flights=original_flights,
            passengers=[Passenger(first_name="Sara", last_name="Doe", dob="1990-04-05")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=620)],
            created_at=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        flights_update = [
            FlightInfo(flight_number="HAT001", date="2024-07-01"),
            FlightInfo(flight_number="HAT002", date="2024-07-10")
        ]
        # Should not raise
        try:
            guard_consistency_across_flight_segments(history, api, reservation_id, "business", flights_update, "credit_card_7815826")
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: expected no PolicyViolationException, but got: {e.message}")
