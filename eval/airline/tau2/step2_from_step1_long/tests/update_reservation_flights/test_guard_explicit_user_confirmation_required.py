from unittest.mock import MagicMock, patch
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.update_reservation_flights.guard_explicit_user_confirmation_required import guard_explicit_user_confirmation_required
from airline.airline_types import *
from airline.i_airline import *
from datetime import datetime, timedelta

class TestExplicitUserConfirmationRequired:
    def test_compliance_user_says_yes_after_details(self):
        """
        Policy: "Before using ToolX for reservation updates including flights, baggage, cabin class, or passenger information, ensure you present all action details to the user in a clear manner and receive their explicit confirmation (yes) to proceed."
        Example: "The agent presents the updated flight itinerary, cabin class changes, and passenger adjustments in detail and waits for the user to reply 'yes' before proceeding, ensuring compliance with the required user confirmation."
        """
        history = MagicMock()
        history.ask_bool.return_value = True  # User explicitly said 'yes'
        api = MagicMock(spec=I_Airline)
        # Mock get_reservation_details
        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="sara_doe_496",
            origin="SFO",
            destination="JFK",
            flight_type="round_trip",
            cabin="business",
            flights=[ReservationFlight(flight_number="HAT001", origin="SFO", destination="JFK", date="2024-05-01", price=500)],
            passengers=[Passenger(first_name="Sara", last_name="Doe", dob="1990-04-05")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=500)],
            created_at=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None
        flights = [FlightInfo(flight_number="HAT001", date="2024-05-01")]
        # Should NOT raise
        try:
            guard_explicit_user_confirmation_required(
                history,
                api,
                reservation_id="ZFA04Y",
                cabin="business",
                flights=flights,
                payment_id="credit_card_7815826"
            )
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: Expected compliance, but got PolicyViolationException: {e.message}")

    def test_compliance_confirmation_after_email(self):
        """
        Policy: "Before using ToolX for reservation updates including flights, baggage, cabin class, or passenger information, ensure you present all action details to the user in a clear manner and receive their explicit confirmation (yes) to proceed."
        Example: "User interaction history reveals explicit verbal confirmation ('yes') after presenting action details via email, allowing the update_reservation_flights tool to proceed in accordance with policy."
        """
        history = MagicMock()
        history.ask_bool.return_value = True  # User replied 'yes' via email
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: Reservation(
            reservation_id=reservation_id,
            user_id="user_123",
            origin="LAX",
            destination="JFK",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight(flight_number="HAT002", origin="LAX", destination="JFK", date="2024-06-01", price=300)],
            passengers=[Passenger(first_name="John", last_name="Smith", dob="1985-02-10")],
            payment_history=[Payment(payment_id="gift_card_7815826", amount=300)],
            created_at=(datetime.now() - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        flights = [FlightInfo(flight_number="HAT002", date="2024-06-01")]
        try:
            guard_explicit_user_confirmation_required(
                history,
                api,
                reservation_id="8JX2WO",
                cabin="economy",
                flights=flights,
                payment_id="gift_card_7815826"
            )
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: Expected compliance, but got PolicyViolationException: {e.message}")

    def test_compliance_summary_and_yes(self):
        """
        Policy: "Before using ToolX for reservation updates including flights, baggage, cabin class, or passenger information, ensure you present all action details to the user in a clear manner and receive their explicit confirmation (yes) to proceed."
        Example: "Before confirming flight changes, the system shows a summary detailing new flight segments and asks, 'Do you confirm?' The user responds with 'yes', thereby validating the action and meeting the explicit consent requirement."
        """
        history = MagicMock()
        history.ask_bool.return_value = True  # User said 'yes' after summary
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: Reservation(
            reservation_id=reservation_id,
            user_id="user_456",
            origin="ORD",
            destination="MIA",
            flight_type="one_way",
            cabin="basic_economy",
            flights=[ReservationFlight(flight_number="HAT003", origin="ORD", destination="MIA", date="2024-07-01", price=200)],
            passengers=[Passenger(first_name="Alice", last_name="Brown", dob="1992-11-23")],
            payment_history=[Payment(payment_id="certificate_7815826", amount=200)],
            created_at=(datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=0,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        flights = [FlightInfo(flight_number="HAT003", date="2024-07-01")]
        try:
            guard_explicit_user_confirmation_required(
                history,
                api,
                reservation_id="ORDMIA1",
                cabin="basic_economy",
                flights=flights,
                payment_id="certificate_7815826"
            )
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: Expected compliance, but got PolicyViolationException: {e.message}")

    def test_compliance_email_waits_for_yes(self):
        """
        Policy: "Before using ToolX for reservation updates including flights, baggage, cabin class, or passenger information, ensure you present all action details to the user in a clear manner and receive their explicit confirmation (yes) to proceed."
        Example: "Flight changes are sent to the user's registered email address with clear action details, and the system waits until the user replies 'yes' before executing any update, ensuring compliance with the policy."
        """
        history = MagicMock()
        history.ask_bool.return_value = True  # User replied 'yes' via email
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: Reservation(
            reservation_id=reservation_id,
            user_id="user_789",
            origin="SEA",
            destination="ATL",
            flight_type="round_trip",
            cabin="economy",
            flights=[ReservationFlight(flight_number="HAT004", origin="SEA", destination="ATL", date="2024-08-01", price=400)],
            passengers=[Passenger(first_name="Bob", last_name="Lee", dob="1978-09-12")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=400)],
            created_at=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        flights = [FlightInfo(flight_number="HAT004", date="2024-08-01")]
        try:
            guard_explicit_user_confirmation_required(
                history,
                api,
                reservation_id="SEAATL2",
                cabin="economy",
                flights=flights,
                payment_id="credit_card_7815826"
            )
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: Expected compliance, but got PolicyViolationException: {e.message}")

    def test_compliance_live_chat_yes(self):
        """
        Policy: "Before using ToolX for reservation updates including flights, baggage, cabin class, or passenger information, ensure you present all action details to the user in a clear manner and receive their explicit confirmation (yes) to proceed."
        Example: "A detailed list of updates, including flight, baggage, and cabin class changes, is shown to the user during a live chat, and the agent proceeds only after a clear 'yes' from the user, validating adherence to the explicit confirmation policy."
        """
        history = MagicMock()
        history.ask_bool.return_value = True  # User said 'yes' in live chat
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: Reservation(
            reservation_id=reservation_id,
            user_id="user_321",
            origin="BOS",
            destination="DEN",
            flight_type="one_way",
            cabin="business",
            flights=[ReservationFlight(flight_number="HAT005", origin="BOS", destination="DEN", date="2024-09-01", price=600)],
            passengers=[Passenger(first_name="Carol", last_name="King", dob="1980-03-15")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=600)],
            created_at=(datetime.now() - timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=2,
            insurance="yes",
            status=None
        )
        flights = [FlightInfo(flight_number="HAT005", date="2024-09-01")]
        try:
            guard_explicit_user_confirmation_required(
                history,
                api,
                reservation_id="BOSDEN3",
                cabin="business",
                flights=flights,
                payment_id="credit_card_7815826"
            )
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: Expected compliance, but got PolicyViolationException: {e.message}")

    def test_violation_no_confirmation(self):
        """
        Policy: "Before using ToolX for reservation updates including flights, baggage, cabin class, or passenger information, ensure you present all action details to the user in a clear manner and receive their explicit confirmation (yes) to proceed."
        Example: "An agent updates the flight details of a reservation without asking the user for confirmation, proceeding with changes based on assumed preferences, which violates the requirement for explicit user consent."
        """
        history = MagicMock()
        history.ask_bool.return_value = False  # User did NOT say 'yes'
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: Reservation(
            reservation_id=reservation_id,
            user_id="user_111",
            origin="SFO",
            destination="JFK",
            flight_type="round_trip",
            cabin="business",
            flights=[ReservationFlight(flight_number="HAT006", origin="SFO", destination="JFK", date="2024-10-01", price=700)],
            passengers=[Passenger(first_name="Eve", last_name="White", dob="1995-07-07")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=700)],
            created_at=(datetime.now() - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=1,
            insurance="no",
            status=None
        )
        flights = [FlightInfo(flight_number="HAT006", date="2024-10-01")]
        with pytest.raises(PolicyViolationException):
            guard_explicit_user_confirmation_required(
                history,
                api,
                reservation_id="SFOJFK4",
                cabin="business",
                flights=flights,
                payment_id="credit_card_7815826"
            )

    def test_violation_auto_update_no_details(self):
        """
        Policy: "Before using ToolX for reservation updates including flights, baggage, cabin class, or passenger information, ensure you present all action details to the user in a clear manner and receive their explicit confirmation (yes) to proceed."
        Example: "The system automatically applies updates to the reservation based on recent user activity without presenting details or receiving explicit confirmation, failing to adhere to the explicit confirmation policy."
        """
        history = MagicMock()
        history.ask_bool.return_value = False  # No explicit confirmation
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: Reservation(
            reservation_id=reservation_id,
            user_id="user_222",
            origin="LAX",
            destination="ORD",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight(flight_number="HAT007", origin="LAX", destination="ORD", date="2024-11-01", price=350)],
            passengers=[Passenger(first_name="Frank", last_name="Green", dob="1988-12-30")],
            payment_history=[Payment(payment_id="gift_card_7815826", amount=350)],
            created_at=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=0,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        flights = [FlightInfo(flight_number="HAT007", date="2024-11-01")]
        with pytest.raises(PolicyViolationException):
            guard_explicit_user_confirmation_required(
                history,
                api,
                reservation_id="LAXORD5",
                cabin="economy",
                flights=flights,
                payment_id="gift_card_7815826"
            )

    def test_violation_no_explicit_yes(self):
        """
        Policy: "Before using ToolX for reservation updates including flights, baggage, cabin class, or passenger information, ensure you present all action details to the user in a clear manner and receive their explicit confirmation (yes) to proceed."
        Example: "Updates to the cabin class and passenger information are executed without the user explicitly saying 'yes', after merely highlighting them, leading to non-compliance with the explicit consent requirement."
        """
        history = MagicMock()
        history.ask_bool.return_value = False  # User did not say 'yes'
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: Reservation(
            reservation_id=reservation_id,
            user_id="user_333",
            origin="ATL",
            destination="SEA",
            flight_type="round_trip",
            cabin="basic_economy",
            flights=[ReservationFlight(flight_number="HAT008", origin="ATL", destination="SEA", date="2024-12-01", price=250)],
            passengers=[Passenger(first_name="Grace", last_name="Black", dob="1993-05-21")],
            payment_history=[Payment(payment_id="certificate_7815826", amount=250)],
            created_at=(datetime.now() - timedelta(days=15)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        flights = [FlightInfo(flight_number="HAT008", date="2024-12-01")]
        with pytest.raises(PolicyViolationException):
            guard_explicit_user_confirmation_required(
                history,
                api,
                reservation_id="ATLSEA6",
                cabin="basic_economy",
                flights=flights,
                payment_id="certificate_7815826"
            )

    def test_violation_implicit_consent(self):
        """
        Policy: "Before using ToolX for reservation updates including flights, baggage, cabin class, or passenger information, ensure you present all action details to the user in a clear manner and receive their explicit confirmation (yes) to proceed."
        Example: "A reservation update is initiated after receiving implicit consent from phrases like 'okay' or 'sounds good', rather than a clear 'yes', which does not meet the policy's explicit confirmation standard."
        """
        history = MagicMock()
        history.ask_bool.return_value = False  # Only implicit consent, not 'yes'
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: Reservation(
            reservation_id=reservation_id,
            user_id="user_444",
            origin="DEN",
            destination="BOS",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight(flight_number="HAT009", origin="DEN", destination="BOS", date="2025-01-01", price=450)],
            passengers=[Passenger(first_name="Henry", last_name="Stone", dob="1982-08-19")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=450)],
            created_at=(datetime.now() - timedelta(days=20)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        flights = [FlightInfo(flight_number="HAT009", date="2025-01-01")]
        with pytest.raises(PolicyViolationException):
            guard_explicit_user_confirmation_required(
                history,
                api,
                reservation_id="DENBOS7",
                cabin="economy",
                flights=flights,
                payment_id="credit_card_7815826"
            )

    def test_violation_no_prompt_before_finalize(self):
        """
        Policy: "Before using ToolX for reservation updates including flights, baggage, cabin class, or passenger information, ensure you present all action details to the user in a clear manner and receive their explicit confirmation (yes) to proceed."
        Example: "The system pre-fills all updates regarding flights and baggage but does not prompt the user for confirmation before finalizing, violating the policy's demand for explicit consent."
        """
        history = MagicMock()
        history.ask_bool.return_value = False  # No prompt for confirmation
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: Reservation(
            reservation_id=reservation_id,
            user_id="user_555",
            origin="JFK",
            destination="LAX",
            flight_type="round_trip",
            cabin="business",
            flights=[ReservationFlight(flight_number="HAT010", origin="JFK", destination="LAX", date="2025-02-01", price=800)],
            passengers=[Passenger(first_name="Ivy", last_name="Gold", dob="1975-04-30")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=800)],
            created_at=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=3,
            nonfree_baggages=2,
            insurance="yes",
            status=None
        )
        flights = [FlightInfo(flight_number="HAT010", date="2025-02-01")]
        with pytest.raises(PolicyViolationException):
            guard_explicit_user_confirmation_required(
                history,
                api,
                reservation_id="JFKLAX8",
                cabin="business",
                flights=flights,
                payment_id="credit_card_7815826"
            )
