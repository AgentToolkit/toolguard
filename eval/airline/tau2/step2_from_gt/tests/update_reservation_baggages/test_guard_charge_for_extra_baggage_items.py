from unittest.mock import MagicMock, patch
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.update_reservation_baggages.guard_charge_for_extra_baggage_items import guard_charge_for_extra_baggage_items
from airline.i_airline import *
from airline.airline_types import *
from datetime import datetime, timedelta

class TestGuardChargeForExtraBaggageItems:

    def test_silver_member_basic_economy_three_bags(self):
        """
        Policy: "Charge for Extra Baggage Items"
        Example: "A silver member with a basic economy ticket asks to update their reservation to include three checked baggages. The first checked bag is free, and the agent correctly applies a $100 charge for the two extra nonfree baggages."
        """
        
        history = MagicMock()
        history.ask_bool.return_value = True

        user = User(
            user_id="user123",
            name=Name(first_name="John", last_name="Doe"),
            address=Address(address1="123 Main St", address2=None, city="New York", country="USA", state="NY", zip="10001"),
            email="john.doe@example.com",
            dob="1980-01-01",
            saved_passengers=[],
            membership="silver",
            payment_methods={"credit_card_123": CreditCard(source="credit_card", id="credit_card_123", brand="visa", last_four="1234")},
            reservations=["res123"]
        )
        reservation = Reservation(
            reservation_id="res123",
            user_id="user123",
            cabin="basic_economy",
            total_baggages=3,
            nonfree_baggages=2,
            payment_history=[],
            passengers=[],
            flights=[],
            origin="JFK",
            destination="LAX",
            flight_type="one_way",
            created_at=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            insurance="no",
            status=None
        )

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "user123" else None
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "res123" else None

        guard_charge_for_extra_baggage_items(history, api, reservation_id="res123", total_baggages=3, nonfree_baggages=2, payment_id="credit_card_123")

    def test_regular_member_basic_economy_one_bag_no_fee(self):
        """
        Policy: "Charge for Extra Baggage Items"
        Example: "A user with a regular membership books a reservation in basic economy and requests to update the baggage to include one checked baggage item without paying any fees."
        """
        
        history = MagicMock()
        history.ask_bool.return_value = True

        user = User(
            user_id="user456",
            name=Name(first_name="Jane", last_name="Smith"),
            address=Address(address1="456 Elm St", address2=None, city="San Francisco", country="USA", state="CA", zip="94101"),
            email="jane.smith@example.com",
            dob="1990-02-02",
            saved_passengers=[],
            membership="regular",
            payment_methods={"credit_card_456": CreditCard(source="credit_card", id="credit_card_456", brand="mastercard", last_four="4567")},
            reservations=["res456"]
        )
        reservation = Reservation(
            reservation_id="res456",
            user_id="user456",
            cabin="basic_economy",
            total_baggages=1,
            nonfree_baggages=1,
            payment_history=[],
            passengers=[],
            flights=[],
            origin="SFO",
            destination="ORD",
            flight_type="round_trip",
            created_at=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            insurance="yes",
            status=None
        )

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "user456" else None
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "res456" else None

        with pytest.raises(PolicyViolationException):
            guard_charge_for_extra_baggage_items(history, api, reservation_id="res456", total_baggages=1, nonfree_baggages=1, payment_id="credit_card_456")

    def test_silver_member_economy_four_extra_bags_no_payment(self):
        """
        Policy: "Charge for Extra Baggage Items"
        Example: "The airline agent updates the baggage information for a silver member traveling in economy class to include four more baggage items than the free allowance, without using any payment method for the extra charges."
        """
        
        history = MagicMock()
        history.ask_bool.return_value = True

        user = User(
            user_id="user789",
            name=Name(first_name="Alice", last_name="Johnson"),
            address=Address(address1="789 Pine St", address2=None, city="Los Angeles", country="USA", state="CA", zip="90001"),
            email="alice.johnson@example.com",
            dob="1985-03-03",
            saved_passengers=[],
            membership="silver",
            payment_methods={"gift_card_789": GiftCard(source="gift_card", id="gift_card_789", amount=200)},
            reservations=["res789"]
        )
        reservation = Reservation(
            reservation_id="res789",
            user_id="user789",
            cabin="economy",
            total_baggages=6,
            nonfree_baggages=4,
            payment_history=[],
            passengers=[],
            flights=[],
            origin="LAX",
            destination="MIA",
            flight_type="one_way",
            created_at=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            insurance="no",
            status=None
        )

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "user789" else None
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "res789" else None

        with pytest.raises(PolicyViolationException):
            guard_charge_for_extra_baggage_items(history, api, reservation_id="res789", total_baggages=6, nonfree_baggages=4, payment_id="gift_card_789")
