from unittest import TestCase
from unittest.mock import MagicMock, patch
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.book_reservation.guard_passenger_information_completeness import guard_passenger_information_completeness
from airline.i_airline import *
from airline.airline_types import *
from datetime import datetime, timedelta

class TestPassengerInformationCompleteness(TestCase):

    def setUp(self):
        # mock the history service:
        self.history = MagicMock()
        self.history.ask_bool.return_value = True

        # mock other tools function return values 
        user = User(user_id="sara_doe_496", name=Name(first_name="Sara", last_name="Doe"), address=Address(address1="123 Main St", address2=None, city="San Francisco", country="USA", state="CA", zip="94105"), email="sara.doe@example.com", dob="1990-04-05", payment_methods={}, saved_passengers=[], membership="regular", reservations=[])

        self.api = MagicMock(spec=I_Airline)
        self.api.get_user_details.side_effect = lambda user_id: user if user_id == "sara_doe_496" else None

    def test_successful_passenger_information_collection(self):
        """
        Policy: "Ensure all required passenger details are collected. Limit to five passengers per reservation, with details including first name, last name, and date of birth."
        Example: "An agent successfully gathers and verifies all required passenger information including first name, last name, and date of birth for each of the five passengers."
        """
        
        passengers = [
            Passenger(first_name="John", last_name="Doe", dob="1985-05-15"),
            Passenger(first_name="Jane", last_name="Doe", dob="1990-06-20"),
            Passenger(first_name="Jim", last_name="Beam", dob="1982-07-25"),
            Passenger(first_name="Jack", last_name="Daniels", dob="1975-08-30"),
            Passenger(first_name="Jill", last_name="Valentine", dob="1995-09-10")
        ]

        flights = [FlightInfo(flight_number="HAT001", date="2024-05-01")]
        payment_methods = [Payment(payment_id="pay_001", amount=500)]

        # invoke function under test
        guard_passenger_information_completeness(self.history, self.api, "sara_doe_496", "SFO", "JFK", "round_trip", "economy", flights, passengers, payment_methods, 2, 1, "yes")

    def test_exceeding_passenger_limit(self):
        """
        Policy: "Ensure all required passenger details are collected. Limit to five passengers per reservation, with details including first name, last name, and date of birth."
        Example: "An agent attempts to book a reservation using BookReservation for six passengers instead of the allowed maximum of five."
        """
        
        passengers = [
            Passenger(first_name="John", last_name="Doe", dob="1985-05-15"),
            Passenger(first_name="Jane", last_name="Doe", dob="1990-06-20"),
            Passenger(first_name="Jim", last_name="Beam", dob="1982-07-25"),
            Passenger(first_name="Jack", last_name="Daniels", dob="1975-08-30"),
            Passenger(first_name="Jill", last_name="Valentine", dob="1995-09-10"),
            Passenger(first_name="Jake", last_name="Peralta", dob="1988-10-15")
        ]

        flights = [FlightInfo(flight_number="HAT001", date="2024-05-01")]
        payment_methods = [Payment(payment_id="pay_001", amount=500)]

        # invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_passenger_information_completeness(self.history, self.api, "sara_doe_496", "SFO", "JFK", "round_trip", "economy", flights, passengers, payment_methods, 2, 1, "yes")

    def test_missing_date_of_birth(self):
        """
        Policy: "Ensure all required passenger details are collected. Limit to five passengers per reservation, with details including first name, last name, and date of birth."
        Example: "An agent calls BookReservation with the passenger details incomplete, missing the date of birth for each passenger."
        """

        passengers = [
            Passenger(first_name="John", last_name="Doe", dob=""),
            Passenger(first_name="Jane", last_name="Doe", dob=""),
            Passenger(first_name="Jim", last_name="Beam", dob=""),
            Passenger(first_name="Jack", last_name="Daniels", dob=""),
            Passenger(first_name="Jill", last_name="Valentine", dob="")
        ]

        flights = [FlightInfo(flight_number="HAT001", date="2024-05-01")]
        payment_methods = [Payment(payment_id="pay_001", amount=500)]

        # invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_passenger_information_completeness(self.history, self.api, "sara_doe_496", "SFO", "JFK", "round_trip", "economy", flights, passengers, payment_methods, 2, 1, "yes")

    def test_no_passengers(self):
        """
        Policy: "Ensure all required passenger details are collected. Limit to five passengers per reservation, with details including first name, last name, and date of birth."
        Example: "An agent attempts to book a reservation with no passengers."
        """
        passengers = []

        flights = [FlightInfo(flight_number="HAT001", date="2024-05-01")]
        payment_methods = [Payment(payment_id="pay_001", amount=500)]

        # invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_passenger_information_completeness(self.history, self.api, "sara_doe_496", "SFO", "JFK", "round_trip", "economy", flights, passengers, payment_methods, 2, 1, "yes")

    def test_missing_first_name(self):
        """
        Policy: "Ensure all required passenger details are collected. Limit to five passengers per reservation, with details including first name, last name, and date of birth."
        Example: "Booking a reservation for one passenger with missing first name information."
        """
        passengers = [Passenger(first_name="", last_name="Doe", dob="1985-05-15")]

        flights = [FlightInfo(flight_number="HAT001", date="2024-05-01")]
        payment_methods = [Payment(payment_id="pay_001", amount=500)]

        # invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_passenger_information_completeness(self.history, self.api, "sara_doe_496", "SFO", "JFK", "round_trip", "economy", flights, passengers, payment_methods, 2, 1, "yes")

    def test_missing_last_name(self):
        """
        Policy: "Ensure all required passenger details are collected. Limit to five passengers per reservation, with details including first name, last name, and date of birth."
        Example: "Booking a reservation for one passenger with missing last name information."
        """
        passengers = [Passenger(first_name="John", last_name="", dob="1985-05-15")]

        flights = [FlightInfo(flight_number="HAT001", date="2024-05-01")]
        payment_methods = [Payment(payment_id="pay_001", amount=500)]

        # invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_passenger_information_completeness(self.history, self.api, "sara_doe_496", "SFO", "JFK", "round_trip", "economy", flights, passengers, payment_methods, 2, 1, "yes")
