from unittest.mock import MagicMock, patch
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.update_reservation_passengers.guard_ensure_user_confirmation import guard_ensure_user_confirmation
from airline.airline_types import *
from airline.i_airline import *
from datetime import datetime, timedelta

class TestEnsureUserConfirmation:
    def test_email_confirmation_received(self):
        """
        Policy: "Before using ToolX to update passenger information in the booking database, an airline agent must present the details of the changes to the user and obtain explicit confirmation ('yes') from them before proceeding."
        Example: "Before updating the passenger information for reservation 'ZFA04Y', the airline agent sends an email detailing the changes and receives a reply from the user confirming 'yes' before proceeding."
        """
        history = MagicMock()
        history.ask_bool.return_value = True  # User confirmed 'yes'
        api = MagicMock(spec=I_Airline)
        # Mock get_reservation_details to return a valid reservation
        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="user_123",
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight(flight_number="HAT001", origin="SFO", destination="JFK", date="2024-06-01", price=500)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1980-01-01")],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == "ZFA04Y" else None
        passengers = [Passenger(first_name="Jane", last_name="Doe", dob="1990-02-02")]
        # Should not raise
        try:
            guard_ensure_user_confirmation(history, api, "ZFA04Y", passengers)
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: Expected no PolicyViolationException when user confirmation is present. Got: {e.message}")

    def test_no_confirmation_raises_exception(self):
        """
        Policy: "Before using ToolX to update passenger information in the booking database, an airline agent must present the details of the changes to the user and obtain explicit confirmation ('yes') from them before proceeding."
        Example: "An airline agent updates the passenger information for a reservation without displaying the changes to the user or obtaining explicit confirmation from them, violating the policy that requires a 'yes' confirmation before proceeding."
        """
        history = MagicMock()
        history.ask_bool.return_value = False  # User did NOT confirm
        api = MagicMock(spec=I_Airline)
        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="user_123",
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight(flight_number="HAT001", origin="SFO", destination="JFK", date="2024-06-01", price=500)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1980-01-01")],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == "ZFA04Y" else None
        passengers = [Passenger(first_name="Jane", last_name="Doe", dob="1990-02-02")]
        with pytest.raises(PolicyViolationException):
            guard_ensure_user_confirmation(history, api, "ZFA04Y", passengers)

    def test_update_without_any_communication(self):
        """
        Policy: "Before using ToolX to update passenger information in the booking database, an airline agent must present the details of the changes to the user and obtain explicit confirmation ('yes') from them before proceeding."
        Example: "Without any prior communication or explicit confirmation, an airline agent updates John Doe's reservation details, assuming agreement."
        """
        history = MagicMock()
        history.ask_bool.return_value = False  # No communication, so no confirmation
        api = MagicMock(spec=I_Airline)
        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="user_123",
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight(flight_number="HAT001", origin="SFO", destination="JFK", date="2024-06-01", price=500)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1980-01-01")],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == "ZFA04Y" else None
        passengers = [Passenger(first_name="Jane", last_name="Doe", dob="1990-02-02")]
        with pytest.raises(PolicyViolationException):
            guard_ensure_user_confirmation(history, api, "ZFA04Y", passengers)

    def test_chat_confirmation_received(self):
        """
        Policy: "Before using ToolX to update passenger information in the booking database, an airline agent must present the details of the changes to the user and obtain explicit confirmation ('yes') from them before proceeding."
        Example: "Prior to modification, the agent sends the updated passenger list via chat and waits for the user to type 'yes', confirming the changes."
        """
        history = MagicMock()
        history.ask_bool.return_value = True  # User confirmed 'yes' in chat
        api = MagicMock(spec=I_Airline)
        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="user_123",
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight(flight_number="HAT001", origin="SFO", destination="JFK", date="2024-06-01", price=500)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1980-01-01")],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == "ZFA04Y" else None
        passengers = [Passenger(first_name="Jane", last_name="Doe", dob="1990-02-02")]
        try:
            guard_ensure_user_confirmation(history, api, "ZFA04Y", passengers)
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: Expected no PolicyViolationException when user confirmation is present in chat. Got: {e.message}")
