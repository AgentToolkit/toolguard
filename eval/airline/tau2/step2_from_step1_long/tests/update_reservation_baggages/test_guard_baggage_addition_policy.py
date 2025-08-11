from unittest.mock import MagicMock, patch
import pytest
from datetime import datetime, timedelta
from rt_toolguard.data_types import PolicyViolationException
from airline.update_reservation_baggages.guard_baggage_addition_policy import guard_baggage_addition_policy
from airline.airline_types import *
from airline.i_airline import *

class TestGuardBaggageAdditionPolicy:
    # --- COMPLIANCE EXAMPLES ---
    def test_gold_member_business_class_adds_2_bags(self):
        """
        Policy: "Increasing checked bags from 2 to 4 on reservation 'ZFA04Y': A gold member in business class adds 2 additional nonfree bags using a stored credit card, correctly applying fees according to policy."
        """
        history = MagicMock()
        history.ask_bool.return_value = True
        history.did_tool_return_value.return_value = True
        history.was_tool_called.return_value = True

        # Mock reservation details
        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="gold_user_001",
            origin="JFK",
            destination="LAX",
            flight_type="round_trip",
            cabin="business",
            flights=[ReservationFlight(flight_number="HAT001", origin="JFK", destination="LAX", date="2024-06-01", price=500)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1980-01-01")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=1000)],
            created_at=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=0,
            insurance="yes",
            status=None
        )
        # Mock user details
        user = User(
            user_id="gold_user_001",
            name=Name(first_name="John", last_name="Doe"),
            address=Address(address1="123 Main St", address2=None, city="NYC", country="USA", state="NY", zip="10001"),
            email="john.doe@example.com",
            dob="1980-01-01",
            payment_methods={"credit_card_7815826": CreditCard(source="credit_card", id="credit_card_7815826", brand="visa", last_four="1234")},
            saved_passengers=[Passenger(first_name="John", last_name="Doe", dob="1980-01-01")],
            membership="gold",
            reservations=["ZFA04Y"]
        )
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None
        api.get_user_details.side_effect = lambda user_id: user if user_id == "gold_user_001" else None
        api.calculate.side_effect = lambda expression: "100" if "2 * 50" in expression else "0"

        # Call function under test
        guard_baggage_addition_policy(
            history,
            api,
            reservation_id="ZFA04Y",
            total_baggages=4,
            nonfree_baggages=2,
            payment_id="credit_card_7815826"
        )

    def test_silver_member_economy_adds_2_bags(self):
        """
        Policy: "For reservation 'ZFA04Y', updating with a silver member traveling in economy by adding 2 checked bags, correctly adjusting total_baggages to 4 and nonfree_baggages to 2, using a stored gift card for payment as per policy."
        """
        history = MagicMock()
        history.ask_bool.return_value = True
        history.did_tool_return_value.return_value = True
        history.was_tool_called.return_value = True

        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="silver_user_002",
            origin="JFK",
            destination="LAX",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight(flight_number="HAT002", origin="JFK", destination="LAX", date="2024-06-02", price=400)],
            passengers=[Passenger(first_name="Jane", last_name="Smith", dob="1990-02-02")],
            payment_history=[Payment(payment_id="gift_card_7815826", amount=500)],
            created_at=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        user = User(
            user_id="silver_user_002",
            name=Name(first_name="Jane", last_name="Smith"),
            address=Address(address1="456 Elm St", address2=None, city="NYC", country="USA", state="NY", zip="10002"),
            email="jane.smith@example.com",
            dob="1990-02-02",
            payment_methods={"gift_card_7815826": GiftCard(source="gift_card", id="gift_card_7815826", amount=200)},
            saved_passengers=[Passenger(first_name="Jane", last_name="Smith", dob="1990-02-02")],
            membership="silver",
            reservations=["ZFA04Y"]
        )
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None
        api.get_user_details.side_effect = lambda user_id: user if user_id == "silver_user_002" else None
        api.calculate.side_effect = lambda expression: "100" if "2 * 50" in expression else "0"

        guard_baggage_addition_policy(
            history,
            api,
            reservation_id="ZFA04Y",
            total_baggages=4,
            nonfree_baggages=2,
            payment_id="gift_card_7815826"
        )

    # --- VIOLATION EXAMPLES ---
    def test_cannot_remove_checked_bags(self):
        """
        Policy: "Updating reservation with ID 'ZFA04Y' to reduce the total checked bags from 3 to 2, violating the policy that prevents removing checked bags."
        """
        history = MagicMock()
        history.ask_bool.return_value = True
        history.did_tool_return_value.return_value = True
        history.was_tool_called.return_value = True

        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="regular_user_003",
            origin="JFK",
            destination="LAX",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight(flight_number="HAT003", origin="JFK", destination="LAX", date="2024-06-03", price=300)],
            passengers=[Passenger(first_name="Alice", last_name="Brown", dob="1985-03-03")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=300)],
            created_at=(datetime.now() - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=3,
            nonfree_baggages=1,
            insurance="no",
            status=None
        )
        user = User(
            user_id="regular_user_003",
            name=Name(first_name="Alice", last_name="Brown"),
            address=Address(address1="789 Oak St", address2=None, city="NYC", country="USA", state="NY", zip="10003"),
            email="alice.brown@example.com",
            dob="1985-03-03",
            payment_methods={"credit_card_7815826": CreditCard(source="credit_card", id="credit_card_7815826", brand="mastercard", last_four="5678")},
            saved_passengers=[Passenger(first_name="Alice", last_name="Brown", dob="1985-03-03")],
            membership="regular",
            reservations=["ZFA04Y"]
        )
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None
        api.get_user_details.side_effect = lambda user_id: user if user_id == "regular_user_003" else None
        api.calculate.side_effect = lambda expression: "0"

        with pytest.raises(PolicyViolationException):
            guard_baggage_addition_policy(
                history,
                api,
                reservation_id="ZFA04Y",  # Attempting to reduce bags
                total_baggages=2,
                nonfree_baggages=1,
                payment_id="credit_card_7815826"
            )

    def test_new_payment_method_not_in_profile(self):
        """
        Policy: "Attempting to use a new payment method not stored in user profile for baggage fees when updating reservation 'ZFA04Y', violating the policy requiring existing payment methods."
        """
        history = MagicMock()
        history.ask_bool.return_value = True
        history.did_tool_return_value.return_value = True
        history.was_tool_called.return_value = True

        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="regular_user_004",
            origin="JFK",
            destination="LAX",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight(flight_number="HAT004", origin="JFK", destination="LAX", date="2024-06-04", price=350)],
            passengers=[Passenger(first_name="Bob", last_name="White", dob="1975-04-04")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=350)],
            created_at=(datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        user = User(
            user_id="regular_user_004",
            name=Name(first_name="Bob", last_name="White"),
            address=Address(address1="321 Pine St", address2=None, city="NYC", country="USA", state="NY", zip="10004"),
            email="bob.white@example.com",
            dob="1975-04-04",
            payment_methods={"credit_card_7815826": CreditCard(source="credit_card", id="credit_card_7815826", brand="visa", last_four="4321")},
            saved_passengers=[Passenger(first_name="Bob", last_name="White", dob="1975-04-04")],
            membership="regular",
            reservations=["ZFA04Y"]
        )
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None
        api.get_user_details.side_effect = lambda user_id: user if user_id == "regular_user_004" else None
        api.calculate.side_effect = lambda expression: "50"

        with pytest.raises(PolicyViolationException):
            guard_baggage_addition_policy(
                history,
                api,
                reservation_id="ZFA04Y",
                total_baggages=2,
                nonfree_baggages=1,
                payment_id="debit_card_123456"  # Not in user profile
            )
