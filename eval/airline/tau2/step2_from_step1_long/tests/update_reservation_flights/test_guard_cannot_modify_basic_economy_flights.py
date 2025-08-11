from unittest.mock import MagicMock
import pytest
from datetime import datetime, timedelta
from rt_toolguard.data_types import PolicyViolationException
from airline.update_reservation_flights.guard_cannot_modify_basic_economy_flights import guard_cannot_modify_basic_economy_flights
from airline.airline_types import *
from airline.i_airline import *

class TestGuardCannotModifyBasicEconomyFlights:
    
    def test_update_business_reservation_same_origin_destination_trip_type(self):
        """
        Policy: "Basic economy flights in a reservation cannot be modified at all. For reservations that are not classified as basic economy, modifications are allowed but must not change the origin, destination, or trip type."
        Example: "An agent successfully updates a 'business' reservation by changing the flight times, keeping the same origin 'SFO' and destination 'JFK' without altering the trip type from 'round_trip', ensuring compliance with the policy."
        """
        history = MagicMock()
        reservation_id = "ZFA04Y"
        payment_id = "credit_card_123456"
        cabin = "business"
        flights = [FlightInfo(flight_number="HAT001", date="2024-07-01")]
        # Original reservation
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_001",
            origin="SFO",
            destination="JFK",
            flight_type="round_trip",
            cabin="business",
            flights=[ReservationFlight(flight_number="HAT001", origin="SFO", destination="JFK", date="2024-07-01", price=500)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[Payment(payment_id=payment_id, amount=500)],
            created_at=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        # Should not raise
        try:
            guard_cannot_modify_basic_economy_flights(history, api, reservation_id, cabin, flights, payment_id)
        except PolicyViolationException as e:
            pytest.fail(f"Business reservation update with same origin/destination/trip type should be allowed. Exception: {e}")

    def test_update_business_reservation_change_destination(self):
        """
        Policy: "Basic economy flights in a reservation cannot be modified at all. For reservations that are not classified as basic economy, modifications are allowed but must not change the origin, destination, or trip type."
        Example: "A user submits a request to change the flights in a business class reservation by altering the destination from 'SFO' to 'NYC', breaking the rule against changing destinations in non-basic reservations."
        """
        history = MagicMock()
        reservation_id = "ZFA04Y"
        payment_id = "credit_card_123456"
        cabin = "business"
        flights = [FlightInfo(flight_number="HAT002", date="2024-07-02")]
        # Original reservation
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_001",
            origin="SFO",
            destination="JFK",
            flight_type="round_trip",
            cabin="business",
            flights=[ReservationFlight(flight_number="HAT001", origin="SFO", destination="JFK", date="2024-07-01", price=500)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[Payment(payment_id=payment_id, amount=500)],
            created_at=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        # Should raise
        with pytest.raises(PolicyViolationException):
            guard_cannot_modify_basic_economy_flights(history, api, reservation_id, cabin, flights, payment_id)

    def test_update_basic_economy_reservation_any_change(self):
        """
        Policy: "Basic economy flights in a reservation cannot be modified at all."
        Example: "A user attempts to change a reservation with basic economy flights by providing a new itinerary with updated origin and destination details, violating the restriction on modifying basic economy flights."
        """
        history = MagicMock()
        reservation_id = "BASIC123"
        payment_id = "credit_card_654321"
        cabin = "basic_economy"
        flights = [FlightInfo(flight_number="HAT003", date="2024-07-03")]
        # Original reservation
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_002",
            origin="LAX",
            destination="ORD",
            flight_type="one_way",
            cabin="basic_economy",
            flights=[ReservationFlight(flight_number="HAT003", origin="LAX", destination="ORD", date="2024-07-03", price=200)],
            passengers=[Passenger(first_name="Jane", last_name="Smith", dob="1985-05-05")],
            payment_history=[Payment(payment_id=payment_id, amount=200)],
            created_at=(datetime.now() - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=0,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        # Should raise
        with pytest.raises(PolicyViolationException):
            guard_cannot_modify_basic_economy_flights(history, api, reservation_id, cabin, flights, payment_id)

    def test_update_economy_reservation_change_trip_type(self):
        """
        Policy: "For reservations that are not classified as basic economy, modifications are allowed but must not change the origin, destination, or trip type."
        Example: "An agent attempts to update a reservation classified as 'economy' by changing the trip type from 'round_trip' to 'one_way', which violates the policy of maintaining trip type for non-basic reservations."
        """
        history = MagicMock()
        reservation_id = "ECO123"
        payment_id = "credit_card_789012"
        cabin = "economy"
        flights = [FlightInfo(flight_number="HAT004", date="2024-07-04")]
        # Original reservation
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_003",
            origin="BOS",
            destination="MIA",
            flight_type="round_trip",
            cabin="economy",
            flights=[ReservationFlight(flight_number="HAT004", origin="BOS", destination="MIA", date="2024-07-04", price=300)],
            passengers=[Passenger(first_name="Alice", last_name="Brown", dob="1995-03-03")],
            payment_history=[Payment(payment_id=payment_id, amount=300)],
            created_at=(datetime.now() - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        # Simulate a change in trip type by modifying the returned reservation's flight_type
        changed_reservation = reservation.copy(update={"flight_type": "one_way"})
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda rid: changed_reservation if rid == reservation_id else None
        # Should raise
        with pytest.raises(PolicyViolationException):
            guard_cannot_modify_basic_economy_flights(history, api, reservation_id, cabin, flights, payment_id)

    def test_update_economy_reservation_add_baggage(self):
        """
        Policy: "For reservations that are not classified as basic economy, modifications are allowed but must not change the origin, destination, or trip type."
        Example: "An agent processes an update for an economy reservation by adding extra baggage allowance, ensuring the flight itinerary remains intact with the original destination 'BOS' and trip type 'round_trip', fulfilling the policy requirements."
        """
        history = MagicMock()
        reservation_id = "ECO124"
        payment_id = "credit_card_789013"
        cabin = "economy"
        flights = [FlightInfo(flight_number="HAT005", date="2024-07-05")]
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_004",
            origin="SEA",
            destination="BOS",
            flight_type="round_trip",
            cabin="economy",
            flights=[ReservationFlight(flight_number="HAT005", origin="SEA", destination="BOS", date="2024-07-05", price=350)],
            passengers=[Passenger(first_name="Bob", last_name="White", dob="1980-12-12")],
            payment_history=[Payment(payment_id=payment_id, amount=350)],
            created_at=(datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=1,
            insurance="no",
            status=None
        )
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        # Should not raise
        try:
            guard_cannot_modify_basic_economy_flights(history, api, reservation_id, cabin, flights, payment_id)
        except PolicyViolationException as e:
            pytest.fail(f"Economy reservation update with same origin/destination/trip type should be allowed. Exception: {e}")

    def test_update_basic_economy_reservation_change_cabin(self):
        """
        Policy: "Basic economy flights in a reservation cannot be modified at all."
        Example: "An agent tries to update a basic economy flight reservation by changing the cabin class from 'basic_economy' to 'economy', which violates the policy against altering basic economy reservations."
        """
        history = MagicMock()
        reservation_id = "BASIC124"
        payment_id = "credit_card_654322"
        cabin = "economy"  # Attempting to change from basic_economy to economy
        flights = [FlightInfo(flight_number="HAT006", date="2024-07-06")]
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_005",
            origin="DFW",
            destination="PHX",
            flight_type="one_way",
            cabin="basic_economy",
            flights=[ReservationFlight(flight_number="HAT006", origin="DFW", destination="PHX", date="2024-07-06", price=180)],
            passengers=[Passenger(first_name="Carol", last_name="Green", dob="1975-07-07")],
            payment_history=[Payment(payment_id=payment_id, amount=180)],
            created_at=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=0,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        # Should raise
        with pytest.raises(PolicyViolationException):
            guard_cannot_modify_basic_economy_flights(history, api, reservation_id, cabin, flights, payment_id)
