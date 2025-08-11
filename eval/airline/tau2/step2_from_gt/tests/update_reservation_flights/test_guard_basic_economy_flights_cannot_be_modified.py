from unittest.mock import MagicMock, patch
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.update_reservation_flights.guard_basic_economy_flights_cannot_be_modified import guard_basic_economy_flights_cannot_be_modified
from airline.i_airline import *
from airline.airline_types import *
from datetime import datetime, timedelta

class TestGuardBasicEconomyFlightsCannotBeModified:
    
    def test_update_economy_reservation(self):
        """
        Policy: "Basic economy flights cannot be modified."
        Example: "A user requests to update multiple flight segments for their economy reservation."
        """
        # Mock the history service
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock the API
        api = MagicMock(spec=I_Airline)
        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="user_123",
            origin="JFK",
            destination="LAX",
            flight_type="round_trip",
            cabin="economy",
            flights=[ReservationFlight(flight_number="HAT001", origin="JFK", destination="LAX", date="2024-05-01", price=300)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=300)],
            created_at=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None

        # Invoke function under test
        try:
            guard_basic_economy_flights_cannot_be_modified(
                history=history,
                api=api,
                reservation_id="ZFA04Y",
                cabin="economy",
                flights=[FlightInfo(flight_number="HAT001", date="2024-05-01")],
                payment_id="credit_card_7815826"
            )
        except PolicyViolationException:
            pytest.fail("Unexpected PolicyViolationException raised for economy reservation.")

    def test_update_basic_economy_reservation(self):
        """
        Policy: "Basic economy flights cannot be modified."
        Example: "An airline agent tries to call UpdateReservationFlights on a reservation with the cabin class set to 'basic_economy'."
        """
        # Mock the history service
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock the API
        api = MagicMock(spec=I_Airline)
        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="user_123",
            origin="JFK",
            destination="LAX",
            flight_type="round_trip",
            cabin="basic_economy",
            flights=[ReservationFlight(flight_number="HAT001", origin="JFK", destination="LAX", date="2024-05-01", price=300)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=300)],
            created_at=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None

        # Invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_basic_economy_flights_cannot_be_modified(
                history=history,
                api=api,
                reservation_id="ZFA04Y",
                cabin="basic_economy",
                flights=[FlightInfo(flight_number="HAT001", date="2024-05-01")],
                payment_id="credit_card_7815826"
            )
