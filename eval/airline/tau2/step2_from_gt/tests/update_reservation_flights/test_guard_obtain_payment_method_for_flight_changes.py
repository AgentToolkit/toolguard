from unittest.mock import MagicMock, patch
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.update_reservation_flights.guard_obtain_payment_method_for_flight_changes import guard_obtain_payment_method_for_flight_changes
from airline.i_airline import *
from datetime import datetime, timedelta

class TestGuardObtainPaymentMethodForFlightChanges:

    def test_valid_credit_card_in_user_profile(self):
        """
        Policy: "Payment: If the flights are changed, the user needs to provide one gift card or credit card for payment or refund method."
        Example: "An agent is using 'credit_card_1234567', which is present in the user's profile, for handling any potential charges related to the updates."
        """
        
        # Mock the history service
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock the API
        user = User(
            user_id="user_123",
            name=Name(first_name="John", last_name="Doe"),
            address=Address(address1="123 Main St", address2=None, city="Anytown", country="USA", state="CA", zip="12345"),
            email="john.doe@example.com",
            dob="1990-01-01",
            saved_passengers=[],
            membership="regular",
            payment_methods={
                "credit_card_1234567": CreditCard(source="credit_card", id="credit_card_1234567", brand="visa", last_four="1234")
            },
            reservations=["ZFA04Y"]
        )

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "user_123" else None

        # Invoke function under test
        flights = [FlightInfo(flight_number="HAT001", date="2024-05-01")]
        guard_obtain_payment_method_for_flight_changes(history, api, "ZFA04Y", "economy", flights, "credit_card_1234567")

    def test_missing_payment_method_in_user_profile(self):
        """
        Policy: "All payment methods must already be in user profile for safety reasons."
        Example: "An agent updates a reservation using UpdateReservationFlights without confirming that the payment method is stored in the user's profile."
        """
        
        # Mock the history service
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock the API
        user = User(
            user_id="user_123",
            name=Name(first_name="John", last_name="Doe"),
            address=Address(address1="123 Main St", address2=None, city="Anytown", country="USA", state="CA", zip="12345"),
            email="john.doe@example.com",
            dob="1990-01-01",
            saved_passengers=[],
            membership="regular",
            payment_methods={},
            reservations=["ZFA04Y"]
        )

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "user_123" else None

        # Invoke function under test
        flights = [FlightInfo(flight_number="HAT001", date="2024-05-01")]
        with pytest.raises(PolicyViolationException):
            guard_obtain_payment_method_for_flight_changes(history, api, "ZFA04Y", "economy", flights, "credit_card_1234567")

    def test_no_available_payment_methods(self):
        """
        Policy: "The agent should ask for the payment or refund method instead."
        Example: "The agent attempts to modify the whole reservation with new flights using the UpdateReservationFlights tool, but does not have any available payment methods."
        """
        
        # Mock the history service
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock the API
        user = User(
            user_id="user_123",
            name=Name(first_name="John", last_name="Doe"),
            address=Address(address1="123 Main St", address2=None, city="Anytown", country="USA", state="CA", zip="12345"),
            email="john.doe@example.com",
            dob="1990-01-01",
            saved_passengers=[],
            membership="regular",
            payment_methods={},
            reservations=["ZFA04Y"]
        )

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "user_123" else None

        # Invoke function under test
        flights = [FlightInfo(flight_number="HAT001", date="2024-05-01")]
        with pytest.raises(PolicyViolationException):
            guard_obtain_payment_method_for_flight_changes(history, api, "ZFA04Y", "economy", flights, "gift_card_7854421")
