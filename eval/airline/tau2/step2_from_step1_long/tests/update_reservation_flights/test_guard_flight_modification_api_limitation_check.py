from unittest.mock import MagicMock
import pytest
from datetime import datetime, timedelta
from rt_toolguard.data_types import PolicyViolationException
from airline.update_reservation_flights.guard_flight_modification_api_limitation_check import guard_flight_modification_api_limitation_check
from airline.i_airline import *
from airline.airline_types import *

class TestGuardFlightModificationApiLimitationCheck:
    
    def setup_method(self):
        # Common setup for all tests
        self.history = MagicMock()
        self.api = MagicMock(spec=I_Airline)
        # Mock get_reservation_details and get_flight_instance for all tests
        self.api.get_reservation_details = MagicMock()
        self.api.get_flight_instance = MagicMock()

    def test_update_times_preserve_structure(self):
        """
        Policy: "Agents must verify the following before using the Flight Modification API: Basic economy flights are unmodifiable. For other flight reservations, ensure that origin, destination, and trip type remain unchanged from the initial booking. Prices for flight segments retained stay at original rates, not updated by the API. Manual validation of segment prices is required."
        Example: "An agent updates a reservation by changing the flight times while preserving the original cabin class, origin, destination, and trip type, complying with the policy requirements."
        """
        reservation_id = "ZFA04Y"
        cabin = "business"
        payment_id = "credit_card_123456"
        # Original reservation
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_1",
            origin="SFO",
            destination="JFK",
            flight_type="round_trip",
            cabin=cabin,
            flights=[ReservationFlight(flight_number="HAT001", origin="SFO", destination="JFK", date="2024-07-01", price=500)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[Payment(payment_id=payment_id, amount=500)],
            created_at=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        self.api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        # Mock get_flight_instance to return available status
        self.api.get_flight_instance.side_effect = lambda fn, date: FlightDateStatusAvailable(status="available", available_seats={"business": 5, "economy": 10, "basic_economy": 0}, prices={"business": 500, "economy": 300, "basic_economy": 200})
        # New flights (only times changed)
        flights = [FlightInfo(flight_number="HAT001", date="2024-07-01")]
        # Assume manual price validation is done (simulate with history)
        self.history.ask_bool.return_value = True
        # Should not raise
        try:
            guard_flight_modification_api_limitation_check(self.history, self.api, reservation_id, cabin, flights, payment_id)
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: Expected compliance but got PolicyViolationException: {e}")

    def test_update_with_same_origin_destination(self):
        """
        Policy: "Agents must verify the following before using the Flight Modification API: Basic economy flights are unmodifiable. For other flight reservations, ensure that origin, destination, and trip type remain unchanged from the initial booking. Prices for flight segments retained stay at original rates, not updated by the API. Manual validation of segment prices is required."
        Example: "Update reservation flights with the same 'origin' and 'destination', ensuring no changes in basic structure, and manually verify segment prices, complying with the policy."
        """
        reservation_id = "ZFA04Y"
        cabin = "economy"
        payment_id = "credit_card_123456"
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_2",
            origin="LAX",
            destination="ORD",
            flight_type="one_way",
            cabin=cabin,
            flights=[ReservationFlight(flight_number="HAT002", origin="LAX", destination="ORD", date="2024-07-10", price=350)],
            passengers=[Passenger(first_name="Jane", last_name="Smith", dob="1985-05-05")],
            payment_history=[Payment(payment_id=payment_id, amount=350)],
            created_at=(datetime.now() - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        self.api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        self.api.get_flight_instance.side_effect = lambda fn, date: FlightDateStatusAvailable(status="available", available_seats={"business": 2, "economy": 8, "basic_economy": 0}, prices={"business": 600, "economy": 350, "basic_economy": 150})
        flights = [FlightInfo(flight_number="HAT002", date="2024-07-10")]
        self.history.ask_bool.return_value = True
        try:
            guard_flight_modification_api_limitation_check(self.history, self.api, reservation_id, cabin, flights, payment_id)
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: Expected compliance but got PolicyViolationException: {e}")

    def test_additional_segments_preserve_details(self):
        """
        Policy: "Agents must verify the following before using the Flight Modification API: Basic economy flights are unmodifiable. For other flight reservations, ensure that origin, destination, and trip type remain unchanged from the initial booking. Prices for flight segments retained stay at original rates, not updated by the API. Manual validation of segment prices is required."
        Example: "The agent modifies a reservation by adding additional flight segments while original flight details, including trip type and destination, remain unchanged, adhering to the policy."
        """
        reservation_id = "ZFA04Y"
        cabin = "economy"
        payment_id = "credit_card_123456"
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_3",
            origin="SEA",
            destination="MIA",
            flight_type="round_trip",
            cabin=cabin,
            flights=[ReservationFlight(flight_number="HAT003", origin="SEA", destination="MIA", date="2024-07-15", price=400)],
            passengers=[Passenger(first_name="Alice", last_name="Brown", dob="1992-03-03")],
            payment_history=[Payment(payment_id=payment_id, amount=400)],
            created_at=(datetime.now() - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        self.api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        self.api.get_flight_instance.side_effect = lambda fn, date: FlightDateStatusAvailable(status="available", available_seats={"business": 1, "economy": 5, "basic_economy": 0}, prices={"business": 700, "economy": 400, "basic_economy": 250})
        flights = [
            FlightInfo(flight_number="HAT003", date="2024-07-15"),
            FlightInfo(flight_number="HAT004", date="2024-07-16")
        ]
        self.history.ask_bool.return_value = True
        try:
            guard_flight_modification_api_limitation_check(self.history, self.api, reservation_id, cabin, flights, payment_id)
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: Expected compliance but got PolicyViolationException: {e}")

    def test_no_change_segments_manual_price_check(self):
        """
        Policy: "Agents must verify the following before using the Flight Modification API: Basic economy flights are unmodifiable. For other flight reservations, ensure that origin, destination, and trip type remain unchanged from the initial booking. Prices for flight segments retained stay at original rates, not updated by the API. Manual validation of segment prices is required."
        Example: "Keeping the flight segments unchanged and manually verifying that the prices remain the same while modifying flights in a business cabin reservation complies with the policy."
        """
        reservation_id = "ZFA04Y"
        cabin = "business"
        payment_id = "credit_card_123456"
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_4",
            origin="ATL",
            destination="DEN",
            flight_type="one_way",
            cabin=cabin,
            flights=[ReservationFlight(flight_number="HAT005", origin="ATL", destination="DEN", date="2024-07-20", price=450)],
            passengers=[Passenger(first_name="Bob", last_name="White", dob="1980-12-12")],
            payment_history=[Payment(payment_id=payment_id, amount=450)],
            created_at=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        self.api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        self.api.get_flight_instance.side_effect = lambda fn, date: FlightDateStatusAvailable(status="available", available_seats={"business": 3, "economy": 6, "basic_economy": 0}, prices={"business": 450, "economy": 300, "basic_economy": 200})
        flights = [FlightInfo(flight_number="HAT005", date="2024-07-20")]
        self.history.ask_bool.return_value = True
        try:
            guard_flight_modification_api_limitation_check(self.history, self.api, reservation_id, cabin, flights, payment_id)
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: Expected compliance but got PolicyViolationException: {e}")

    def test_update_seat_preference_consistent_trip(self):
        """
        Policy: "Agents must verify the following before using the Flight Modification API: Basic economy flights are unmodifiable. For other flight reservations, ensure that origin, destination, and trip type remain unchanged from the initial booking. Prices for flight segments retained stay at original rates, not updated by the API. Manual validation of segment prices is required."
        Example: "The agent updates a reservation to change seat preference while ensuring the origin, destination, and trip type are consistent with the initial booking, meeting policy criteria."
        """
        reservation_id = "ZFA04Y"
        cabin = "economy"
        payment_id = "credit_card_123456"
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_5",
            origin="BOS",
            destination="PHX",
            flight_type="round_trip",
            cabin=cabin,
            flights=[ReservationFlight(flight_number="HAT006", origin="BOS", destination="PHX", date="2024-07-25", price=380)],
            passengers=[Passenger(first_name="Carol", last_name="Green", dob="1995-07-07")],
            payment_history=[Payment(payment_id=payment_id, amount=380)],
            created_at=(datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        self.api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        self.api.get_flight_instance.side_effect = lambda fn, date: FlightDateStatusAvailable(status="available", available_seats={"business": 2, "economy": 7, "basic_economy": 0}, prices={"business": 500, "economy": 380, "basic_economy": 180})
        flights = [FlightInfo(flight_number="HAT006", date="2024-07-25")]
        self.history.ask_bool.return_value = True
        try:
            guard_flight_modification_api_limitation_check(self.history, self.api, reservation_id, cabin, flights, payment_id)
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: Expected compliance but got PolicyViolationException: {e}")

    def test_basic_economy_unmodifiable(self):
        """
        Policy: "Agents must verify the following before using the Flight Modification API: Basic economy flights are unmodifiable. For other flight reservations, ensure that origin, destination, and trip type remain unchanged from the initial booking. Prices for flight segments retained stay at original rates, not updated by the API. Manual validation of segment prices is required."
        Example: "An agent attempts to use the Flight Modification API to change the cabin class of a reservation booked under 'basic_economy'. This violates the policy since 'basic_economy' flights are unmodifiable."
        """
        reservation_id = "ZFA04Y"
        cabin = "basic_economy"
        payment_id = "credit_card_123456"
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_6",
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin=cabin,
            flights=[ReservationFlight(flight_number="HAT007", origin="SFO", destination="JFK", date="2024-07-30", price=200)],
            passengers=[Passenger(first_name="Eve", last_name="Black", dob="1993-09-09")],
            payment_history=[Payment(payment_id=payment_id, amount=200)],
            created_at=(datetime.now() - timedelta(days=4)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        self.api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        self.api.get_flight_instance.side_effect = lambda fn, date: FlightDateStatusAvailable(status="available", available_seats={"business": 0, "economy": 0, "basic_economy": 1}, prices={"business": 0, "economy": 0, "basic_economy": 200})
        flights = [FlightInfo(flight_number="HAT007", date="2024-07-30")]
        self.history.ask_bool.return_value = True
        with pytest.raises(PolicyViolationException):
            guard_flight_modification_api_limitation_check(self.history, self.api, reservation_id, cabin, flights, payment_id)

    def test_change_origin_violates_policy(self):
        """
        Policy: "Agents must verify the following before using the Flight Modification API: Basic economy flights are unmodifiable. For other flight reservations, ensure that origin, destination, and trip type remain unchanged from the initial booking. Prices for flight segments retained stay at original rates, not updated by the API. Manual validation of segment prices is required."
        Example: "The agent changes the origin from 'SFO' to 'LAX' in a reservation update, violating the policy as the origin must remain unchanged."
        """
        reservation_id = "ZFA04Y"
        cabin = "business"
        payment_id = "credit_card_123456"
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_7",
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin=cabin,
            flights=[ReservationFlight(flight_number="HAT008", origin="SFO", destination="JFK", date="2024-08-01", price=600)],
            passengers=[Passenger(first_name="Frank", last_name="Gray", dob="1988-11-11")],
            payment_history=[Payment(payment_id=payment_id, amount=600)],
            created_at=(datetime.now() - timedelta(days=6)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="yes",
            status=None
        )
        self.api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        self.api.get_flight_instance.side_effect = lambda fn, date: FlightDateStatusAvailable(status="available", available_seats={"business": 2, "economy": 3, "basic_economy": 0}, prices={"business": 600, "economy": 400, "basic_economy": 200})
        # New flights with changed origin
        flights = [FlightInfo(flight_number="HAT008", date="2024-08-01")]
        self.history.ask_bool.return_value = True
        with pytest.raises(PolicyViolationException):
            guard_flight_modification_api_limitation_check(self.history, self.api, reservation_id, cabin, flights, payment_id)

    def test_change_destination_violates_policy(self):
        """
        Policy: "Agents must verify the following before using the Flight Modification API: Basic economy flights are unmodifiable. For other flight reservations, ensure that origin, destination, and trip type remain unchanged from the initial booking. Prices for flight segments retained stay at original rates, not updated by the API. Manual validation of segment prices is required."
        Example: "Changing the destination from 'JFK' to 'BOS' during a reservation update violates the policy because the destination must remain unchanged."
        """
        reservation_id = "ZFA04Y"
        cabin = "business"
        payment_id = "credit_card_123456"
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_8",
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin=cabin,
            flights=[ReservationFlight(flight_number="HAT009", origin="SFO", destination="JFK", date="2024-08-05", price=650)],
            passengers=[Passenger(first_name="Grace", last_name="Blue", dob="1991-02-02")],
            payment_history=[Payment(payment_id=payment_id, amount=650)],
            created_at=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="no",
            status=None
        )
        self.api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        self.api.get_flight_instance.side_effect = lambda fn, date: FlightDateStatusAvailable(status="available", available_seats={"business": 2, "economy": 3, "basic_economy": 0}, prices={"business": 650, "economy": 400, "basic_economy": 200})
        # New flights with changed destination
        flights = [FlightInfo(flight_number="HAT009", date="2024-08-05")]
        self.history.ask_bool.return_value = True
        with pytest.raises(PolicyViolationException):
            guard_flight_modification_api_limitation_check(self.history, self.api, reservation_id, cabin, flights, payment_id)

    def test_change_trip_type_violates_policy(self):
        """
        Policy: "Agents must verify the following before using the Flight Modification API: Basic economy flights are unmodifiable. For other flight reservations, ensure that origin, destination, and trip type remain unchanged from the initial booking. Prices for flight segments retained stay at original rates, not updated by the API. Manual validation of segment prices is required."
        Example: "An agent updates a flight reservation from a 'round_trip' to a 'one_way' trip, violating the policy since the trip type cannot be altered."
        """
        reservation_id = "ZFA04Y"
        cabin = "economy"
        payment_id = "credit_card_123456"
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_9",
            origin="LAX",
            destination="ORD",
            flight_type="round_trip",
            cabin=cabin,
            flights=[ReservationFlight(flight_number="HAT010", origin="LAX", destination="ORD", date="2024-08-10", price=400)],
            passengers=[Passenger(first_name="Henry", last_name="Yellow", dob="1982-06-06")],
            payment_history=[Payment(payment_id=payment_id, amount=400)],
            created_at=(datetime.now() - timedelta(days=8)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="yes",
            status=None
        )
        self.api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        self.api.get_flight_instance.side_effect = lambda fn, date: FlightDateStatusAvailable(status="available", available_seats={"business": 2, "economy": 3, "basic_economy": 0}, prices={"business": 400, "economy": 400, "basic_economy": 200})
        flights = [FlightInfo(flight_number="HAT010", date="2024-08-10")]
        self.history.ask_bool.return_value = True
        with pytest.raises(PolicyViolationException):
            guard_flight_modification_api_limitation_check(self.history, self.api, reservation_id, cabin, flights, payment_id)

    def test_no_manual_price_verification(self):
        """
        Policy: "Agents must verify the following before using the Flight Modification API: Basic economy flights are unmodifiable. For other flight reservations, ensure that origin, destination, and trip type remain unchanged from the initial booking. Prices for flight segments retained stay at original rates, not updated by the API. Manual validation of segment prices is required."
        Example: "An agent uses the API to modify a flight reservation without manually verifying the prices of retained flight segments, violating the policy that requires agents to confirm original rates manually."
        """
        reservation_id = "ZFA04Y"
        cabin = "business"
        payment_id = "credit_card_123456"
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_10",
            origin="SEA",
            destination="MIA",
            flight_type="one_way",
            cabin=cabin,
            flights=[ReservationFlight(flight_number="HAT011", origin="SEA", destination="MIA", date="2024-08-15", price=700)],
            passengers=[Passenger(first_name="Ivy", last_name="Pink", dob="1996-10-10")],
            payment_history=[Payment(payment_id=payment_id, amount=700)],
            created_at=(datetime.now() - timedelta(days=9)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="no",
            status=None
        )
        self.api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        self.api.get_flight_instance.side_effect = lambda fn, date: FlightDateStatusAvailable(status="available", available_seats={"business": 2, "economy": 3, "basic_economy": 0}, prices={"business": 700, "economy": 400, "basic_economy": 200})
        flights = [FlightInfo(flight_number="HAT011", date="2024-08-15")]
        # Simulate manual price check not performed
        self.history.ask_bool.return_value = False
        with pytest.raises(PolicyViolationException):
            guard_flight_modification_api_limitation_check(self.history, self.api, reservation_id, cabin, flights, payment_id)
