from unittest.mock import MagicMock, patch
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.book_reservation.guard_user_id_and_user_profile_verification import guard_user_id_and_user_profile_verification
from airline.i_airline import *
from airline.airline_types import *
from datetime import datetime, timedelta

class TestGuardUserIdAndUserProfileVerification:

    def test_user_id_verification_compliance(self):
        """
        Policy: "Before invoking ToolX (BookReservation), make sure that the user's ID is correctly obtained."
        Example: "An agent receives a user request to book a flight, first verifies the user's ID exists in the system records, and subsequently collects information on trip type, origin, and destination before proceeding with BookReservation."
        """
        # Mock the history service
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock the API and its return values
        user = User(user_id="sara_doe_496", name=Name(first_name="Sara", last_name="Doe"), address=Address(address1="123 Main St", address2=None, city="San Francisco", country="USA", state="CA", zip="94105"), email="sara.doe@example.com", dob="1990-04-05", payment_methods={}, saved_passengers=[], membership="regular", reservations=[])

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "sara_doe_496" else None

        # Invoke function under test
        try:
            guard_user_id_and_user_profile_verification(
                history=history,
                api=api,
                user_id="sara_doe_496",
                origin="SFO",
                destination="JFK",
                flight_type="round_trip",
                cabin="economy",
                flights=[FlightInfo(flight_number="HAT001", date="2024-05-01")],
                passengers=[Passenger(first_name="Sara", last_name="Doe", dob="1990-04-05")],
                payment_methods=[Payment(payment_id="pay_001", amount=500)],
                total_baggages=2,
                nonfree_baggages=1,
                insurance="yes"
            )
        except PolicyViolationException:
            pytest.fail("The function raised PolicyViolationException unexpectedly.")

    def test_incorrect_user_id_raises_exception(self):
        """
        Policy: "Before invoking ToolX (BookReservation), make sure that the user's ID is correctly obtained."
        Example: "The agent attempts to use BookReservation but enters an incorrect user ID that does not exist in the system records."
        """
        # Mock the history service
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock the API and its return values
        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: None

        # Invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_user_id_and_user_profile_verification(
                history=history,
                api=api,
                user_id="incorrect_id",
                origin="SFO",
                destination="JFK",
                flight_type="round_trip",
                cabin="economy",
                flights=[FlightInfo(flight_number="HAT001", date="2024-05-01")],
                passengers=[Passenger(first_name="Sara", last_name="Doe", dob="1990-04-05")],
                payment_methods=[Payment(payment_id="pay_001", amount=500)],
                total_baggages=2,
                nonfree_baggages=1,
                insurance="yes"
            )

    def test_missing_trip_type_raises_exception(self):
        """
        Policy: "After verifying the user ID, gather necessary booking information such as trip type, origin, and destination prior to making the reservation using ToolX."
        Example: "After obtaining the user ID, the agent makes a call to BookReservation without confirming the trip type, thereby not gathering necessary booking information."
        """
        # Mock the history service
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock the API and its return values
        user = User(user_id="sara_doe_496", name=Name(first_name="Sara", last_name="Doe"), address=Address(address1="123 Main St", address2=None, city="San Francisco", country="USA", state="CA", zip="94105"), email="sara.doe@example.com", dob="1990-04-05", payment_methods={}, saved_passengers=[], membership="regular", reservations=[])

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "sara_doe_496" else None

        # Invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_user_id_and_user_profile_verification(
                history=history,
                api=api,
                user_id="sara_doe_496",
                origin="SFO",
                destination="JFK",
                flight_type=None,  # Missing trip type
                cabin="economy",
                flights=[FlightInfo(flight_number="HAT001", date="2024-05-01")],
                passengers=[Passenger(first_name="Sara", last_name="Doe", dob="1990-04-05")],
                payment_methods=[Payment(payment_id="pay_001", amount=500)],
                total_baggages=2,
                nonfree_baggages=1,
                insurance="yes"
            )

    def test_unverified_user_id_raises_exception(self):
        """
        Policy: "Upon receiving an ID query from a user, the agent assumes the ID is correct without verifying it against system records and proceeds to book a reservation, breaching the mandate for ID confirmation."
        Example: "Upon receiving an ID query from a user, the agent assumes the ID is correct without verifying it against system records and proceeds to book a reservation, breaching the mandate for ID confirmation."
        """
        # Mock the history service
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock the API and its return values
        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: None

        # Invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_user_id_and_user_profile_verification(
                history=history,
                api=api,
                user_id="unverified_id",
                origin="SFO",
                destination="JFK",
                flight_type="round_trip",
                cabin="economy",
                flights=[FlightInfo(flight_number="HAT001", date="2024-05-01")],
                passengers=[Passenger(first_name="Sara", last_name="Doe", dob="1990-04-05")],
                payment_methods=[Payment(payment_id="pay_001", amount=500)],
                total_baggages=2,
                nonfree_baggages=1,
                insurance="yes"
            )
