from unittest.mock import MagicMock, patch
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.book_reservation.guard_passenger_information_completeness import guard_passenger_information_completeness
from airline.i_airline import *
from airline.airline_types import *
from datetime import datetime, timedelta

class TestPassengerInformationCompleteness:

    def test_successful_passenger_information_collection(self):
        """
        Policy: "Ensure all required passenger details are collected. Limit to five passengers per reservation, with details including first name, last name, and date of birth."
        Example: "An agent successfully gathers and verifies all required passenger information including first name, last name, and date of birth for each of the five passengers."
        """
        
        # mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True

        # mock other tools function return values 
        user = User(user_id="sara_doe_496", name=Name(first_name="Sara", last_name="Doe"), address=Address(address1="123 Main St", address2=None, city="San Francisco", country="USA", state="CA", zip="94105"), email="sara.doe@example.com", dob="1990-04-05", payment_methods={}, saved_passengers=[], membership="regular", reservations=[])

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "sara_doe_496" else None

        passengers = [
            Passenger(first_name="John", last_name="Doe", dob="1985-05-15"),
            Passenger(first_name="Jane", last_name="Smith", dob="1990-07-20"),
            Passenger(first_name="Emily", last_name="Jones", dob="1992-11-30"),
            Passenger(first_name="Michael", last_name="Brown", dob="1988-03-25"),
            Passenger(first_name="Jessica", last_name="Taylor", dob="1995-09-10")
        ]

        flights = [FlightInfo(flight_number="HAT001", date="2024-05-01")]
        payment_methods = [Payment(payment_id="pay_001", amount=500)]

        # invoke function under test
        guard_passenger_information_completeness(
            history=history,
            api=api,
            user_id="sara_doe_496",
            origin="SFO",
            destination="JFK",
            flight_type="round_trip",
            cabin="economy",
            flights=flights,
            passengers=passengers,
            payment_methods=payment_methods,
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes"
        )

    def test_exceed_passenger_limit(self):
        """
        Policy: "Ensure all required passenger details are collected. Limit to five passengers per reservation, with details including first name, last name, and date of birth."
        Example: "An agent attempts to book a reservation using BookReservation for six passengers instead of the allowed maximum of five."
        """
        
        # mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True

        # mock other tools function return values 
        user = User(user_id="sara_doe_496", name=Name(first_name="Sara", last_name="Doe"), address=Address(address1="123 Main St", address2=None, city="San Francisco", country="USA", state="CA", zip="94105"), email="sara.doe@example.com", dob="1990-04-05", payment_methods={}, saved_passengers=[], membership="regular", reservations=[])

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "sara_doe_496" else None

        passengers = [
            Passenger(first_name="John", last_name="Doe", dob="1985-05-15"),
            Passenger(first_name="Jane", last_name="Smith", dob="1990-07-20"),
            Passenger(first_name="Emily", last_name="Jones", dob="1992-11-30"),
            Passenger(first_name="Michael", last_name="Brown", dob="1988-03-25"),
            Passenger(first_name="Jessica", last_name="Taylor", dob="1995-09-10"),
            Passenger(first_name="Chris", last_name="Wilson", dob="1987-02-14")
        ]

        flights = [FlightInfo(flight_number="HAT001", date="2024-05-01")]
        payment_methods = [Payment(payment_id="pay_001", amount=500)]

        # invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_passenger_information_completeness(
                history=history,
                api=api,
                user_id="sara_doe_496",
                origin="SFO",
                destination="JFK",
                flight_type="round_trip",
                cabin="economy",
                flights=flights,
                passengers=passengers,
                payment_methods=payment_methods,
                total_baggages=2,
                nonfree_baggages=1,
                insurance="yes"
            )

    def test_missing_passenger_dob(self):
        """
        Policy: "Ensure all required passenger details are collected. Limit to five passengers per reservation, with details including first name, last name, and date of birth."
        Example: "An agent calls BookReservation with the passenger details incomplete, missing the date of birth for each passenger."
        """
        
        # mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True

        # mock other tools function return values 
        user = User(user_id="sara_doe_496", name=Name(first_name="Sara", last_name="Doe"), address=Address(address1="123 Main St", address2=None, city="San Francisco", country="USA", state="CA", zip="94105"), email="sara.doe@example.com", dob="1990-04-05", payment_methods={}, saved_passengers=[], membership="regular", reservations=[])

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "sara_doe_496" else None

        passengers = [
            Passenger(first_name="John", last_name="Doe", dob=""),
            Passenger(first_name="Jane", last_name="Smith", dob=""),
            Passenger(first_name="Emily", last_name="Jones", dob=""),
            Passenger(first_name="Michael", last_name="Brown", dob=""),
            Passenger(first_name="Jessica", last_name="Taylor", dob="")
        ]

        flights = [FlightInfo(flight_number="HAT001", date="2024-05-01")]
        payment_methods = [Payment(payment_id="pay_001", amount=500)]

        # invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_passenger_information_completeness(
                history=history,
                api=api,
                user_id="sara_doe_496",
                origin="SFO",
                destination="JFK",
                flight_type="round_trip",
                cabin="economy",
                flights=flights,
                passengers=passengers,
                payment_methods=payment_methods,
                total_baggages=2,
                nonfree_baggages=1,
                insurance="yes"
            )

    def test_no_passengers(self):
        """
        Policy: "Ensure all required passenger details are collected. Limit to five passengers per reservation, with details including first name, last name, and date of birth."
        Example: "An agent attempts to book a reservation with no passengers."
        """
        
        # mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True

        # mock other tools function return values 
        user = User(user_id="sara_doe_496", name=Name(first_name="Sara", last_name="Doe"), address=Address(address1="123 Main St", address2=None, city="San Francisco", country="USA", state="CA", zip="94105"), email="sara.doe@example.com", dob="1990-04-05", payment_methods={}, saved_passengers=[], membership="regular", reservations=[])

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "sara_doe_496" else None

        passengers = []

        flights = [FlightInfo(flight_number="HAT001", date="2024-05-01")]
        payment_methods = [Payment(payment_id="pay_001", amount=500)]

        # invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_passenger_information_completeness(
                history=history,
                api=api,
                user_id="sara_doe_496",
                origin="SFO",
                destination="JFK",
                flight_type="round_trip",
                cabin="economy",
                flights=flights,
                passengers=passengers,
                payment_methods=payment_methods,
                total_baggages=2,
                nonfree_baggages=1,
                insurance="yes"
            )

    def test_missing_first_name(self):
        """
        Policy: "Ensure all required passenger details are collected. Limit to five passengers per reservation, with details including first name, last name, and date of birth."
        Example: "Booking a reservation for one passenger with missing first name information."
        """
        
        # mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True

        # mock other tools function return values 
        user = User(user_id="sara_doe_496", name=Name(first_name="Sara", last_name="Doe"), address=Address(address1="123 Main St", address2=None, city="San Francisco", country="USA", state="CA", zip="94105"), email="sara.doe@example.com", dob="1990-04-05", payment_methods={}, saved_passengers=[], membership="regular", reservations=[])

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "sara_doe_496" else None

        passengers = [Passenger(first_name="", last_name="Doe", dob="1985-05-15")]

        flights = [FlightInfo(flight_number="HAT001", date="2024-05-01")]
        payment_methods = [Payment(payment_id="pay_001", amount=500)]

        # invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_passenger_information_completeness(
                history=history,
                api=api,
                user_id="sara_doe_496",
                origin="SFO",
                destination="JFK",
                flight_type="round_trip",
                cabin="economy",
                flights=flights,
                passengers=passengers,
                payment_methods=payment_methods,
                total_baggages=2,
                nonfree_baggages=1,
                insurance="yes"
            )

    def test_missing_last_name(self):
        """
        Policy: "Ensure all required passenger details are collected. Limit to five passengers per reservation, with details including first name, last name, and date of birth."
        Example: "Booking a reservation for one passenger with missing last name information."
        """
        
        # mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True

        # mock other tools function return values 
        user = User(user_id="sara_doe_496", name=Name(first_name="Sara", last_name="Doe"), address=Address(address1="123 Main St", address2=None, city="San Francisco", country="USA", state="CA", zip="94105"), email="sara.doe@example.com", dob="1990-04-05", payment_methods={}, saved_passengers=[], membership="regular", reservations=[])

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "sara_doe_496" else None

        passengers = [Passenger(first_name="John", last_name="", dob="1985-05-15")]

        flights = [FlightInfo(flight_number="HAT001", date="2024-05-01")]
        payment_methods = [Payment(payment_id="pay_001", amount=500)]

        # invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_passenger_information_completeness(
                history=history,
                api=api,
                user_id="sara_doe_496",
                origin="SFO",
                destination="JFK",
                flight_type="round_trip",
                cabin="economy",
                flights=flights,
                passengers=passengers,
                payment_methods=payment_methods,
                total_baggages=2,
                nonfree_baggages=1,
                insurance="yes"
            )
