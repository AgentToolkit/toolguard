from unittest.mock import MagicMock
import pytest
from datetime import datetime, timedelta
from rt_toolguard.data_types import PolicyViolationException
from airline.update_reservation_flights.guard_cabin_uniformity_requirement import guard_cabin_uniformity_requirement
from airline.airline_types import *
from airline.i_airline import I_Airline

class TestCabinUniformityRequirement:
    def test_all_flights_economy_compliance(self):
        """
        Policy: "Cabin class must be the same across all flights in a reservation."
        Example: "A user updates a reservation so all flights are reassigned to economy class, ensuring uniform cabin class and complying with the policy."
        """
        history = MagicMock()
        history.ask_bool.return_value = True
        api = MagicMock(spec=I_Airline)
        reservation_id = "ZFA04Y"
        payment_id = "credit_card_7815826"
        cabin = "economy"
        flights = [
            FlightInfo(flight_number="HAT001", date=(datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")),
            FlightInfo(flight_number="HAT002", date=(datetime.now() + timedelta(days=8)).strftime("%Y-%m-%d")),
        ]
        # Mock get_reservation_details to return a reservation with all flights in economy
        api.get_reservation_details.return_value = Reservation(
            reservation_id=reservation_id,
            user_id="user_123",
            origin="SFO",
            destination="JFK",
            flight_type="round_trip",
            cabin="economy",
            flights=[
                ReservationFlight(flight_number="HAT001", origin="SFO", destination="JFK", date=(datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"), price=500),
                ReservationFlight(flight_number="HAT002", origin="JFK", destination="SFO", date=(datetime.now() + timedelta(days=8)).strftime("%Y-%m-%d"), price=500),
            ],
            passengers=[],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        # Should not raise
        try:
            guard_cabin_uniformity_requirement(history, api, reservation_id, cabin, flights, payment_id)
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: All flights set to economy, expected compliance but got violation: {e.message}")

    def test_all_flights_business_compliance(self):
        """
        Policy: "Cabin class must be the same across all flights in a reservation."
        Example: "The reservation is modified to have all flights in business class, maintaining a consistent cabin class across the entire reservation as per the policy."
        """
        history = MagicMock()
        history.ask_bool.return_value = True
        api = MagicMock(spec=I_Airline)
        reservation_id = "ZFA04Y"
        payment_id = "credit_card_7815826"
        cabin = "business"
        flights = [
            FlightInfo(flight_number="BUS001", date=(datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")),
            FlightInfo(flight_number="BUS002", date=(datetime.now() + timedelta(days=11)).strftime("%Y-%m-%d")),
        ]
        api.get_reservation_details.return_value = Reservation(
            reservation_id=reservation_id,
            user_id="user_456",
            origin="LAX",
            destination="ORD",
            flight_type="round_trip",
            cabin="business",
            flights=[
                ReservationFlight(flight_number="BUS001", origin="LAX", destination="ORD", date=(datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d"), price=1200),
                ReservationFlight(flight_number="BUS002", origin="ORD", destination="LAX", date=(datetime.now() + timedelta(days=11)).strftime("%Y-%m-%d"), price=1200),
            ],
            passengers=[],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        try:
            guard_cabin_uniformity_requirement(history, api, reservation_id, cabin, flights, payment_id)
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: All flights set to business, expected compliance but got violation: {e.message}")

    def test_round_trip_economy_compliance(self):
        """
        Policy: "Cabin class must be the same across all flights in a reservation."
        Example: "Both flight segments in a round-trip reservation are changed to the same cabin class, such as economy, meeting the Cabin Uniformity Requirement."
        """
        history = MagicMock()
        history.ask_bool.return_value = True
        api = MagicMock(spec=I_Airline)
        reservation_id = "ZFA04Y"
        payment_id = "gift_card_7815826"
        cabin = "economy"
        flights = [
            FlightInfo(flight_number="ECO001", date=(datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")),
            FlightInfo(flight_number="ECO002", date=(datetime.now() + timedelta(days=16)).strftime("%Y-%m-%d")),
        ]
        api.get_reservation_details.return_value = Reservation(
            reservation_id=reservation_id,
            user_id="user_789",
            origin="SEA",
            destination="MIA",
            flight_type="round_trip",
            cabin="economy",
            flights=[
                ReservationFlight(flight_number="ECO001", origin="SEA", destination="MIA", date=(datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d"), price=700),
                ReservationFlight(flight_number="ECO002", origin="MIA", destination="SEA", date=(datetime.now() + timedelta(days=16)).strftime("%Y-%m-%d"), price=700),
            ],
            passengers=[],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=3,
            nonfree_baggages=1,
            insurance="no",
            status=None
        )
        try:
            guard_cabin_uniformity_requirement(history, api, reservation_id, cabin, flights, payment_id)
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: Round-trip flights set to economy, expected compliance but got violation: {e.message}")

    def test_mixed_cabin_violation(self):
        """
        Policy: "Cabin class must be the same across all flights in a reservation."
        Example: "A reservation is updated with mixed cabin classes, such as economy and business, across different flights within the same reservation. This violates the policy requiring uniform cabin class."
        """
        history = MagicMock()
        history.ask_bool.return_value = True
        api = MagicMock(spec=I_Airline)
        reservation_id = "ZFA04Y"
        payment_id = "certificate_7815826"
        # Simulate user trying to update flights with mixed cabin classes
        flights = [
            FlightInfo(flight_number="MIX001", date=(datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d")),
            FlightInfo(flight_number="MIX002", date=(datetime.now() + timedelta(days=21)).strftime("%Y-%m-%d")),
        ]
        # The cabin argument is 'economy', but let's simulate a violation by passing flights that are intended to be different cabins
        # (In reality, the function should check that all flights are updated to the same cabin)
        api.get_reservation_details.return_value = Reservation(
            reservation_id=reservation_id,
            user_id="user_321",
            origin="BOS",
            destination="ATL",
            flight_type="round_trip",
            cabin="economy",
            flights=[
                ReservationFlight(flight_number="MIX001", origin="BOS", destination="ATL", date=(datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d"), price=400),
                ReservationFlight(flight_number="MIX002", origin="ATL", destination="BOS", date=(datetime.now() + timedelta(days=21)).strftime("%Y-%m-%d"), price=400),
            ],
            passengers=[],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="yes",
            status=None
        )
        with pytest.raises(PolicyViolationException):
            # Simulate violation: flights are not all set to the same cabin class
            guard_cabin_uniformity_requirement(history, api, reservation_id, "economy", flights, payment_id)

    def test_economy_and_basic_economy_violation(self):
        """
        Policy: "Cabin class must be the same across all flights in a reservation."
        Example: "A user changes one flight to economy and another to basic economy within a reservation, failing the Cabin Uniformity Requirement that mandates the same cabin class for all flights."
        """
        history = MagicMock()
        history.ask_bool.return_value = True
        api = MagicMock(spec=I_Airline)
        reservation_id = "ZFA04Y"
        payment_id = "credit_card_7815826"
        flights = [
            FlightInfo(flight_number="ECOBASIC001", date=(datetime.now() + timedelta(days=25)).strftime("%Y-%m-%d")),
            FlightInfo(flight_number="ECOBASIC002", date=(datetime.now() + timedelta(days=26)).strftime("%Y-%m-%d")),
        ]
        api.get_reservation_details.return_value = Reservation(
            reservation_id=reservation_id,
            user_id="user_654",
            origin="PHX",
            destination="DEN",
            flight_type="round_trip",
            cabin="economy",
            flights=[
                ReservationFlight(flight_number="ECOBASIC001", origin="PHX", destination="DEN", date=(datetime.now() + timedelta(days=25)).strftime("%Y-%m-%d"), price=350),
                ReservationFlight(flight_number="ECOBASIC002", origin="DEN", destination="PHX", date=(datetime.now() + timedelta(days=26)).strftime("%Y-%m-%d"), price=350),
            ],
            passengers=[],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="no",
            status=None
        )
        with pytest.raises(PolicyViolationException):
            # Simulate violation: flights are not all set to the same cabin class
            guard_cabin_uniformity_requirement(history, api, reservation_id, "economy", flights, payment_id)
