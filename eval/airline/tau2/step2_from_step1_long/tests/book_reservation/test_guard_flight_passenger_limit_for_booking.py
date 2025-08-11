from unittest.mock import MagicMock
import pytest
from datetime import datetime, timedelta
from rt_toolguard.data_types import PolicyViolationException
from airline.book_reservation.guard_flight_passenger_limit_for_booking import guard_flight_passenger_limit_for_booking
from airline.airline_types import FlightInfo, Passenger, Payment
from airline.i_airline import I_Airline

class TestGuardFlightPassengerLimitForBooking:
    # --- Compliance Examples ---

    def test_three_passengers_economy_jfk_sfo(self):
        """
        Policy: "A flight reservation can have at most five passengers, and all must fly the same flights in the same cabin."
        Example: "Booking for three passengers: John Doe, Jane Smith, and Alex Murphy, all flying economy class from JFK to SFO with identical flight segments, fits the maximum passenger limit and same flight itinerary requirement."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        flight_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        flights = [FlightInfo(flight_number="HAT001", date=flight_date)]
        passengers = [
            Passenger(first_name="John", last_name="Doe", dob="1990-01-01"),
            Passenger(first_name="Jane", last_name="Smith", dob="1985-05-12"),
            Passenger(first_name="Alex", last_name="Murphy", dob="1978-09-23"),
        ]
        payment_methods = [Payment(payment_id="pay1", amount=1200)]
        # Should not raise
        guard_flight_passenger_limit_for_booking(
            history, api, "user123", "JFK", "SFO", "one_way", "economy",
            flights, passengers, payment_methods, 3, 1, "no"
        )

    def test_five_passengers_basic_economy_sfo_jfk(self):
        """
        Policy: "A flight reservation can have at most five passengers, and all must fly the same flights in the same cabin."
        Example: "A reservation for five passengers, all flying from SFO to JFK in basic economy, with collected details including first name, last name, and date of birth for each passenger, adheres to the policy's constraints."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        flight_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        flights = [FlightInfo(flight_number="HAT002", date=flight_date)]
        passengers = [
            Passenger(first_name="John", last_name="Doe", dob="1990-01-01"),
            Passenger(first_name="Jane", last_name="Smith", dob="1985-05-12"),
            Passenger(first_name="Alex", last_name="Murphy", dob="1978-09-23"),
            Passenger(first_name="Ella", last_name="Brown", dob="1992-03-15"),
            Passenger(first_name="Chris", last_name="Davis", dob="1988-07-30"),
        ]
        payment_methods = [Payment(payment_id="pay2", amount=2000)]
        guard_flight_passenger_limit_for_booking(
            history, api, "user456", "SFO", "JFK", "one_way", "basic_economy",
            flights, passengers, payment_methods, 5, 2, "yes"
        )

    def test_four_passengers_business_jfk_lax(self):
        """
        Policy: "A flight reservation can have at most five passengers, and all must fly the same flights in the same cabin."
        Example: "Booking for four passengers: John Doe, Jane Smith, Alex Murphy, and Ella Brown from JFK to LAX in business class, all having the exact flight itinerary and cabin. This meets the policy requirements for passenger limits and identical flight itineraries."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        flight_date = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
        flights = [FlightInfo(flight_number="HAT003", date=flight_date)]
        passengers = [
            Passenger(first_name="John", last_name="Doe", dob="1990-01-01"),
            Passenger(first_name="Jane", last_name="Smith", dob="1985-05-12"),
            Passenger(first_name="Alex", last_name="Murphy", dob="1978-09-23"),
            Passenger(first_name="Ella", last_name="Brown", dob="1992-03-15"),
        ]
        payment_methods = [Payment(payment_id="pay3", amount=1800)]
        guard_flight_passenger_limit_for_booking(
            history, api, "user789", "JFK", "LAX", "one_way", "business",
            flights, passengers, payment_methods, 4, 1, "no"
        )

    def test_two_passengers_round_trip_sfo_mia(self):
        """
        Policy: "A flight reservation can have at most five passengers, and all must fly the same flights in the same cabin."
        Example: "Two passengers, John Doe and Jane Smith, fly together on a round_trip from SFO to MIA in economy class, maintaining identical flight itineraries and cabin, complying with the policy."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        outbound_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        return_date = (datetime.now() + timedelta(days=12)).strftime("%Y-%m-%d")
        flights = [
            FlightInfo(flight_number="HAT004", date=outbound_date),
            FlightInfo(flight_number="HAT005", date=return_date)
        ]
        passengers = [
            Passenger(first_name="John", last_name="Doe", dob="1990-01-01"),
            Passenger(first_name="Jane", last_name="Smith", dob="1985-05-12"),
        ]
        payment_methods = [Payment(payment_id="pay4", amount=900)]
        guard_flight_passenger_limit_for_booking(
            history, api, "user321", "SFO", "MIA", "round_trip", "economy",
            flights, passengers, payment_methods, 2, 0, "yes"
        )

    def test_four_passengers_basic_economy_sfo_jfk(self):
        """
        Policy: "A flight reservation can have at most five passengers, and all must fly the same flights in the same cabin."
        Example: "One reservation for four passengers all flying from SFO to JFK in basic economy class, with first name, last name, and date of birth collected for each. The reservation complies with passenger limits and identical flight requirements."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        flight_date = (datetime.now() + timedelta(days=8)).strftime("%Y-%m-%d")
        flights = [FlightInfo(flight_number="HAT006", date=flight_date)]
        passengers = [
            Passenger(first_name="John", last_name="Doe", dob="1990-01-01"),
            Passenger(first_name="Jane", last_name="Smith", dob="1985-05-12"),
            Passenger(first_name="Alex", last_name="Murphy", dob="1978-09-23"),
            Passenger(first_name="Ella", last_name="Brown", dob="1992-03-15"),
        ]
        payment_methods = [Payment(payment_id="pay5", amount=1600)]
        guard_flight_passenger_limit_for_booking(
            history, api, "user654", "SFO", "JFK", "one_way", "basic_economy",
            flights, passengers, payment_methods, 4, 1, "no"
        )

    # --- Violation Examples ---

    def test_six_passengers_exceeds_limit(self):
        """
        Policy: "A flight reservation can have at most five passengers, and all must fly the same flights in the same cabin."
        Example: "A reservation is attempted for six passengers: John Doe, Jane Smith, Alex Murphy, Ella Brown, Chris Davis, and Emily White, which exceeds the maximum allowed five passengers per reservation."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        flight_date = (datetime.now() + timedelta(days=9)).strftime("%Y-%m-%d")
        flights = [FlightInfo(flight_number="HAT007", date=flight_date)]
        passengers = [
            Passenger(first_name="John", last_name="Doe", dob="1990-01-01"),
            Passenger(first_name="Jane", last_name="Smith", dob="1985-05-12"),
            Passenger(first_name="Alex", last_name="Murphy", dob="1978-09-23"),
            Passenger(first_name="Ella", last_name="Brown", dob="1992-03-15"),
            Passenger(first_name="Chris", last_name="Davis", dob="1988-07-30"),
            Passenger(first_name="Emily", last_name="White", dob="1995-11-11"),
        ]
        payment_methods = [Payment(payment_id="pay6", amount=2400)]
        with pytest.raises(PolicyViolationException):
            guard_flight_passenger_limit_for_booking(
                history, api, "user999", "JFK", "SFO", "one_way", "economy",
                flights, passengers, payment_methods, 6, 2, "no"
            )

    def test_mixed_cabin_classes(self):
        """
        Policy: "A flight reservation can have at most five passengers, and all must fly the same flights in the same cabin."
        Example: "A reservation is made for four passengers: John Doe, Jane Smith, Alex Murphy, and Ella Brown, with John flying business class and the others flying economy. Cabin classes must be the same for all passengers within a reservation."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        flight_date = (datetime.now() + timedelta(days=11)).strftime("%Y-%m-%d")
        flights = [FlightInfo(flight_number="HAT008", date=flight_date)]
        passengers = [
            Passenger(first_name="John", last_name="Doe", dob="1990-01-01"),
            Passenger(first_name="Jane", last_name="Smith", dob="1985-05-12"),
            Passenger(first_name="Alex", last_name="Murphy", dob="1978-09-23"),
            Passenger(first_name="Ella", last_name="Brown", dob="1992-03-15"),
        ]
        payment_methods = [Payment(payment_id="pay7", amount=1800)]
        # Simulate violation by passing 'business' as cabin but expecting others to be 'economy' (policy violation)
        with pytest.raises(PolicyViolationException):
            guard_flight_passenger_limit_for_booking(
                history, api, "user888", "JFK", "LAX", "one_way", "business",
                flights, passengers, payment_methods, 4, 1, "no"
            )

    def test_different_flight_itineraries(self):
        """
        Policy: "A flight reservation can have at most five passengers, and all must fly the same flights in the same cabin."
        Example: "Three passengers, John Doe, Jane Smith, and Alex Murphy, have different flight itineraries: John and Jane are flying from JFK to SFO, and Alex is flying from LAX to SFO. All passengers must share the same flight itinerary."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        flight_date1 = (datetime.now() + timedelta(days=13)).strftime("%Y-%m-%d")
        flight_date2 = (datetime.now() + timedelta(days=13)).strftime("%Y-%m-%d")
        flights = [
            FlightInfo(flight_number="HAT009", date=flight_date1),
            FlightInfo(flight_number="HAT010", date=flight_date2)
        ]
        passengers = [
            Passenger(first_name="John", last_name="Doe", dob="1990-01-01"),
            Passenger(first_name="Jane", last_name="Smith", dob="1985-05-12"),
            Passenger(first_name="Alex", last_name="Murphy", dob="1978-09-23"),
        ]
        payment_methods = [Payment(payment_id="pay8", amount=1500)]
        # Simulate violation by providing flights that do not match for all passengers
        with pytest.raises(PolicyViolationException):
            guard_flight_passenger_limit_for_booking(
                history, api, "user777", "JFK", "SFO", "one_way", "economy",
                flights, passengers, payment_methods, 3, 1, "no"
            )

    def test_different_flight_types(self):
        """
        Policy: "A flight reservation can have at most five passengers, and all must fly the same flights in the same cabin."
        Example: "Booking for two passengers, John Doe and Jane Smith, with different flight types: John on a 'one_way' ticket and Jane on a 'round_trip' ticket. Flight types must be identical among passengers in the reservation."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        outbound_date = (datetime.now() + timedelta(days=6)).strftime("%Y-%m-%d")
        return_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
        flights = [
            FlightInfo(flight_number="HAT011", date=outbound_date),
            FlightInfo(flight_number="HAT012", date=return_date)
        ]
        passengers = [
            Passenger(first_name="John", last_name="Doe", dob="1990-01-01"),
            Passenger(first_name="Jane", last_name="Smith", dob="1985-05-12"),
        ]
        payment_methods = [Payment(payment_id="pay9", amount=1000)]
        # Simulate violation by passing 'one_way' as flight_type but expecting one passenger to have 'round_trip' (policy violation)
        with pytest.raises(PolicyViolationException):
            guard_flight_passenger_limit_for_booking(
                history, api, "user555", "SFO", "JFK", "one_way", "economy",
                flights, passengers, payment_methods, 2, 0, "no"
            )

    def test_partial_flight_itinerary(self):
        """
        Policy: "A flight reservation can have at most five passengers, and all must fly the same flights in the same cabin."
        Example: "A reservation for five passengers includes one passenger flying only part of the shared flight itinerary. All passengers are required to fly all shared flights together."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        flight_date1 = (datetime.now() + timedelta(days=16)).strftime("%Y-%m-%d")
        flight_date2 = (datetime.now() + timedelta(days=17)).strftime("%Y-%m-%d")
        flights = [
            FlightInfo(flight_number="HAT013", date=flight_date1),
            FlightInfo(flight_number="HAT014", date=flight_date2)
        ]
        passengers = [
            Passenger(first_name="John", last_name="Doe", dob="1990-01-01"),
            Passenger(first_name="Jane", last_name="Smith", dob="1985-05-12"),
            Passenger(first_name="Alex", last_name="Murphy", dob="1978-09-23"),
            Passenger(first_name="Ella", last_name="Brown", dob="1992-03-15"),
            Passenger(first_name="Chris", last_name="Davis", dob="1988-07-30"),
        ]
        payment_methods = [Payment(payment_id="pay10", amount=2200)]
        # Simulate violation by having one passenger not on all flights (policy violation)
        with pytest.raises(PolicyViolationException):
            guard_flight_passenger_limit_for_booking(
                history, api, "user444", "JFK", "LAX", "round_trip", "business",
                flights, passengers, payment_methods, 5, 2, "yes"
            )
