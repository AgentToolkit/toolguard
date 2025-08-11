from unittest.mock import MagicMock, patch
import pytest
from datetime import datetime, timedelta
from rt_toolguard.data_types import PolicyViolationException, ChatHistory
from airline.update_reservation_baggages.guard_explicit_confirmation_for_baggage_update import guard_explicit_confirmation_for_baggage_update
from airline.airline_types import *
from airline.i_airline import *

class TestExplicitConfirmationForBaggageUpdate:
    def test_update_baggages_with_explicit_confirmation(self):
        """
        Policy: "Before invoking the 'update_reservation_baggages' tool to update baggage information in a reservation, ensure you list all changes and receive explicit user confirmation (yes) to proceed."
        Example: "A user asks to update reservation 'ZFA04Y' baggages. The system lists changes: increasing total baggages from 2 to 3, nonfree from 0 to 2, using payment method 'certificate_7815826'. User explicitly confirms 'yes' and the operation proceeds."
        """
        # Mock chat history to simulate explicit confirmation
        history = MagicMock(spec=ChatHistory)
        history.ask_bool.return_value = True  # User confirms 'yes'
        # Mock dependent tool: get_reservation_details
        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="user_001",
            origin="JFK",
            destination="LAX",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight(flight_number="HAT001", origin="JFK", destination="LAX", date="2024-06-01", price=350)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[Payment(payment_id="certificate_7815826", amount=100)],
            created_at=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None
        # Should not raise exception
        try:
            guard_explicit_confirmation_for_baggage_update(
                history,
                api,
                reservation_id="ZFA04Y",
                total_baggages=3,
                nonfree_baggages=2,
                payment_id="certificate_7815826"
            )
        except PolicyViolationException as e:
            pytest.fail(f"Explicit confirmation test failed: Expected no exception, got {e.message}")

    def test_update_baggages_without_explicit_confirmation(self):
        """
        Policy: "Before invoking the 'update_reservation_baggages' tool to update baggage information in a reservation, ensure you list all changes and receive explicit user confirmation (yes) to proceed."
        Example: "A user provides a reservation ID 'ZFA04Y' to update baggage details without explicitly confirming the changes. The system proceeds to update the total baggages to 3 and nonfree baggages to 1 using the payment method 'credit_card_7815826' without asking for explicit confirmation."
        """
        # Mock chat history to simulate NO explicit confirmation
        history = MagicMock(spec=ChatHistory)
        history.ask_bool.return_value = False  # User does NOT confirm
        # Mock dependent tool: get_reservation_details
        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="user_001",
            origin="JFK",
            destination="LAX",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight(flight_number="HAT001", origin="JFK", destination="LAX", date="2024-06-01", price=350)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=100)],
            created_at=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None
        # Should raise PolicyViolationException
        with pytest.raises(PolicyViolationException):
            guard_explicit_confirmation_for_baggage_update(
                history,
                api,
                reservation_id="ZFA04Y",
                total_baggages=3,
                nonfree_baggages=1,
                payment_id="credit_card_7815826"
            )

    def test_update_baggages_without_listing_changes(self):
        """
        Policy: "Before invoking the 'update_reservation_baggages' tool to update baggage information in a reservation, ensure you list all changes and receive explicit user confirmation (yes) to proceed."
        Example: "An agent wishes to update the baggage count by reducing total baggages from 5 to 3 using reservation ID 'T125HG' and payment method 'gift_card_123456', but does not list the changes beforehand or seek affirmation from the user."
        """
        history = MagicMock(spec=ChatHistory)
        history.ask_bool.return_value = False  # No confirmation
        reservation = Reservation(
            reservation_id="T125HG",
            user_id="user_002",
            origin="SFO",
            destination="ORD",
            flight_type="round_trip",
            cabin="business",
            flights=[ReservationFlight(flight_number="HAT002", origin="SFO", destination="ORD", date="2024-06-10", price=700)],
            passengers=[Passenger(first_name="Jane", last_name="Smith", dob="1985-05-05")],
            payment_history=[Payment(payment_id="gift_card_123456", amount=200)],
            created_at=(datetime.now() - timedelta(days=20)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=5,
            nonfree_baggages=2,
            insurance="yes",
            status=None
        )
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "T125HG" else None
        with pytest.raises(PolicyViolationException):
            guard_explicit_confirmation_for_baggage_update(
                history,
                api,
                reservation_id="T125HG",
                total_baggages=3,
                nonfree_baggages=2,
                payment_id="gift_card_123456"
            )

    def test_update_baggages_immediate_modification_no_confirmation(self):
        """
        Policy: "Before invoking the 'update_reservation_baggages' tool to update baggage information in a reservation, ensure you list all changes and receive explicit user confirmation (yes) to proceed."
        Example: "User requests to change reservation 'XJ43MS' baggage details and the agent immediately proceeds with modifying nonfree baggages to 2, without listing these adjustments or waiting for a user to say 'yes' for confirmation."
        """
        history = MagicMock(spec=ChatHistory)
        history.ask_bool.return_value = False  # No confirmation
        reservation = Reservation(
            reservation_id="XJ43MS",
            user_id="user_003",
            origin="ATL",
            destination="SEA",
            flight_type="one_way",
            cabin="basic_economy",
            flights=[ReservationFlight(flight_number="HAT003", origin="ATL", destination="SEA", date="2024-06-15", price=250)],
            passengers=[Passenger(first_name="Alice", last_name="Brown", dob="1995-07-07")],
            payment_history=[Payment(payment_id="gift_card_987654", amount=150)],
            created_at=(datetime.now() - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=4,
            nonfree_baggages=1,
            insurance="no",
            status=None
        )
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "XJ43MS" else None
        with pytest.raises(PolicyViolationException):
            guard_explicit_confirmation_for_baggage_update(
                history,
                api,
                reservation_id="XJ43MS",
                total_baggages=4,
                nonfree_baggages=2,
                payment_id="gift_card_987654"
            )

    def test_update_baggages_no_listing_no_confirmation(self):
        """
        Policy: "Before invoking the 'update_reservation_baggages' tool to update baggage information in a reservation, ensure you list all changes and receive explicit user confirmation (yes) to proceed."
        Example: "The reservation update tool is utilized to change baggage information on reservation 'ABCD123' from a total of 2 baggages to 4 without outlining all changes and obtaining user approval."
        """
        history = MagicMock(spec=ChatHistory)
        history.ask_bool.return_value = False  # No confirmation
        reservation = Reservation(
            reservation_id="ABCD123",
            user_id="user_004",
            origin="MIA",
            destination="DEN",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight(flight_number="HAT004", origin="MIA", destination="DEN", date="2024-06-20", price=400)],
            passengers=[Passenger(first_name="Bob", last_name="White", dob="1980-12-12")],
            payment_history=[Payment(payment_id="certificate_112233", amount=120)],
            created_at=(datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ABCD123" else None
        with pytest.raises(PolicyViolationException):
            guard_explicit_confirmation_for_baggage_update(
                history,
                api,
                reservation_id="ABCD123",
                total_baggages=4,
                nonfree_baggages=0,
                payment_id="certificate_112233"
            )
