from unittest.mock import MagicMock
import pytest
from datetime import datetime, timedelta
from rt_toolguard.data_types import PolicyViolationException
from airline.book_reservation.guard_user_confirmation_before_database_update import guard_user_confirmation_before_database_update
from airline.airline_types import FlightInfo, Passenger, Payment
from airline.i_airline import I_Airline

class TestGuardUserConfirmationBeforeDatabaseUpdate:
    def test_compliance_explicit_confirmation_before_booking(self):
        """
        Policy: "Before taking any actions that update the booking database (booking, modifying flights, editing baggage, upgrading cabin class, or updating passenger information), you must list the action details and obtain explicit user confirmation (yes) to proceed."
        Example: "Before finalizing a new reservation for Emily, including flight details, passenger names, and baggage information, the system displays all changes to Emily and obtains her explicit 'yes' confirmation to proceed with the booking."
        """
        # Mock chat history to simulate explicit 'yes' confirmation
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock API (no tool dependencies for this policy)
        api = MagicMock(spec=I_Airline)

        # Populate all required fields
        user_id = "emily_123"
        origin = "SFO"
        destination = "JFK"
        flight_type = "round_trip"
        cabin = "economy"
        flights = [FlightInfo(flight_number="HAT001", date=(datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"))]
        passengers = [Passenger(first_name="Emily", last_name="Stone", dob="1990-04-05")]
        payment_methods = [Payment(payment_id="pay_001", amount=500)]
        total_baggages = 2
        nonfree_baggages = 1
        insurance = "yes"

        # Should NOT raise exception
        try:
            guard_user_confirmation_before_database_update(
                history, api, user_id, origin, destination, flight_type, cabin,
                flights, passengers, payment_methods, total_baggages, nonfree_baggages, insurance
            )
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: Expected compliance, but got PolicyViolationException: {e.message}")

    def test_violation_no_confirmation_before_booking(self):
        """
        Policy: "Before taking any actions that update the booking database (booking, modifying flights, editing baggage, upgrading cabin class, or updating passenger information), you must list the action details and obtain explicit user confirmation (yes) to proceed."
        Example: "The system attempts to book a reservation and update the flight details without displaying them to the user first. John does not get the chance to review or confirm these changes before they are applied. It proceeds without obtaining an affirmative 'yes' from John."
        """
        # Mock chat history to simulate NO confirmation
        history = MagicMock()
        history.ask_bool.return_value = False

        api = MagicMock(spec=I_Airline)

        user_id = "john_456"
        origin = "LAX"
        destination = "ORD"
        flight_type = "one_way"
        cabin = "business"
        flights = [FlightInfo(flight_number="HAT002", date=(datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d"))]
        passengers = [Passenger(first_name="John", last_name="Doe", dob="1985-09-12")]
        payment_methods = [Payment(payment_id="pay_002", amount=800)]
        total_baggages = 1
        nonfree_baggages = 1
        insurance = "no"

        with pytest.raises(PolicyViolationException):
            guard_user_confirmation_before_database_update(
                history, api, user_id, origin, destination, flight_type, cabin,
                flights, passengers, payment_methods, total_baggages, nonfree_baggages, insurance
            )

    def test_compliance_confirmation_before_baggage_edit(self):
        """
        Policy: "Before taking any actions that update the booking database (booking, modifying flights, editing baggage, upgrading cabin class, or updating passenger information), you must list the action details and obtain explicit user confirmation (yes) to proceed."
        Example: "Jane wants to change her seat to economy class and add an additional baggage item to her reservation. The system provides a detailed summary of these changes and asks Jane to confirm with a 'yes' before proceeding."
        """
        history = MagicMock()
        history.ask_bool.return_value = True
        api = MagicMock(spec=I_Airline)
        user_id = "jane_789"
        origin = "SEA"
        destination = "BOS"
        flight_type = "one_way"
        cabin = "economy"
        flights = [FlightInfo(flight_number="HAT003", date=(datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d"))]
        passengers = [Passenger(first_name="Jane", last_name="Smith", dob="1992-11-23")]
        payment_methods = [Payment(payment_id="pay_003", amount=300)]
        total_baggages = 2
        nonfree_baggages = 2
        insurance = "no"
        try:
            guard_user_confirmation_before_database_update(
                history, api, user_id, origin, destination, flight_type, cabin,
                flights, passengers, payment_methods, total_baggages, nonfree_baggages, insurance
            )
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: Expected compliance, but got PolicyViolationException: {e.message}")

    def test_violation_no_confirmation_on_baggage_update(self):
        """
        Policy: "Before taking any actions that update the booking database (booking, modifying flights, editing baggage, upgrading cabin class, or updating passenger information), you must list the action details and obtain explicit user confirmation (yes) to proceed."
        Example: "The system updates the number of non-free baggage items directly based on the user's preferences without explicitly asking for a 'yes' confirmation. This violates the policy by not requesting confirmation before making database changes."
        """
        history = MagicMock()
        history.ask_bool.return_value = False
        api = MagicMock(spec=I_Airline)
        user_id = "mike_321"
        origin = "ATL"
        destination = "DEN"
        flight_type = "round_trip"
        cabin = "basic_economy"
        flights = [FlightInfo(flight_number="HAT004", date=(datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"))]
        passengers = [Passenger(first_name="Mike", last_name="Brown", dob="1988-07-15")]
        payment_methods = [Payment(payment_id="pay_004", amount=200)]
        total_baggages = 3
        nonfree_baggages = 3
        insurance = "yes"
        with pytest.raises(PolicyViolationException):
            guard_user_confirmation_before_database_update(
                history, api, user_id, origin, destination, flight_type, cabin,
                flights, passengers, payment_methods, total_baggages, nonfree_baggages, insurance
            )
