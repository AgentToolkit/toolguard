from unittest.mock import MagicMock, patch
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.update_reservation_baggages.guard_payment_methods_are_pre_authorized import guard_payment_methods_are_pre_authorized
from airline.i_airline import *
from datetime import datetime, timedelta

class TestGuardPaymentMethodsArePreAuthorized:

    def test_credit_card_in_user_profile(self):
        """
        Policy: "Payment Methods Are Pre-Authorized"
        Example: "Updating a reservation providing a credit card that is listed in the user's profile."
        """
        
        history = MagicMock()
        history.ask_bool.return_value = True

        user = User(
            user_id="user_123",
            name=Name(first_name="John", last_name="Doe"),
            address=Address(address1="123 Main St", address2=None, city="Anytown", country="USA", state="CA", zip="12345"),
            email="john.doe@example.com",
            dob="1990-01-01",
            payment_methods={
                "credit_card_7815826": CreditCard(source="credit_card", id="credit_card_7815826", brand="visa", last_four="1234")
            },
            saved_passengers=[],
            membership="regular",
            reservations=["ZFA04Y"]
        )

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "user_123" else None

        guard_payment_methods_are_pre_authorized(
            history=history,
            api=api,
            reservation_id="ZFA04Y",
            total_baggages=2,
            nonfree_baggages=1,
            payment_id="credit_card_7815826"
        )

    def test_gift_card_not_in_user_profile(self):
        """
        Policy: "Payment Methods Are Pre-Authorized"
        Example: "A request to UpdateReservationBaggages uses a gift card that is not stored in the user's profile."
        """
        
        history = MagicMock()
        history.ask_bool.return_value = True

        user = User(
            user_id="user_123",
            name=Name(first_name="John", last_name="Doe"),
            address=Address(address1="123 Main St", address2=None, city="Anytown", country="USA", state="CA", zip="12345"),
            email="john.doe@example.com",
            dob="1990-01-01",
            payment_methods={},
            saved_passengers=[],
            membership="regular",
            reservations=["ZFA04Y"]
        )

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "user_123" else None

        with pytest.raises(PolicyViolationException):
            guard_payment_methods_are_pre_authorized(
                history=history,
                api=api,
                reservation_id="ZFA04Y",
                total_baggages=2,
                nonfree_baggages=1,
                payment_id="gift_card_7815826"
            )

    def test_multiple_credit_cards(self):
        """
        Policy: "Payment Methods Are Pre-Authorized"
        Example: "The agent uses two credit cards in a single reservation to pay for additional baggage charges."
        """
        
        history = MagicMock()
        history.ask_bool.return_value = True

        user = User(
            user_id="user_123",
            name=Name(first_name="John", last_name="Doe"),
            address=Address(address1="123 Main St", address2=None, city="Anytown", country="USA", state="CA", zip="12345"),
            email="john.doe@example.com",
            dob="1990-01-01",
            payment_methods={
                "credit_card_7815826": CreditCard(source="credit_card", id="credit_card_7815826", brand="visa", last_four="1234"),
                "credit_card_7815827": CreditCard(source="credit_card", id="credit_card_7815827", brand="mastercard", last_four="5678")
            },
            saved_passengers=[],
            membership="regular",
            reservations=["ZFA04Y"]
        )

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "user_123" else None

        with pytest.raises(PolicyViolationException):
            guard_payment_methods_are_pre_authorized(
                history=history,
                api=api,
                reservation_id="ZFA04Y",
                total_baggages=2,
                nonfree_baggages=1,
                payment_id="credit_card_7815826,credit_card_7815827"
            )

    def test_no_payment_id_provided(self):
        """
        Policy: "Payment Methods Are Pre-Authorized"
        Example: "Updating a reservation without providing a payment id"
        """
        
        history = MagicMock()
        history.ask_bool.return_value = True

        user = User(
            user_id="user_123",
            name=Name(first_name="John", last_name="Doe"),
            address=Address(address1="123 Main St", address2=None, city="Anytown", country="USA", state="CA", zip="12345"),
            email="john.doe@example.com",
            dob="1990-01-01",
            payment_methods={
                "credit_card_7815826": CreditCard(source="credit_card", id="credit_card_7815826", brand="visa", last_four="1234")
            },
            saved_passengers=[],
            membership="regular",
            reservations=["ZFA04Y"]
        )

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "user_123" else None

        with pytest.raises(PolicyViolationException):
            guard_payment_methods_are_pre_authorized(
                history=history,
                api=api,
                reservation_id="ZFA04Y",
                total_baggages=2,
                nonfree_baggages=1,
                payment_id=""
            )

    def test_travel_certificate_and_gift_card(self):
        """
        Policy: "Payment Methods Are Pre-Authorized"
        Example: "The agent updates the baggage information using one pre-authorized travel certificate from the user's profile and an accompanying gift card."
        """
        
        history = MagicMock()
        history.ask_bool.return_value = True

        user = User(
            user_id="user_123",
            name=Name(first_name="John", last_name="Doe"),
            address=Address(address1="123 Main St", address2=None, city="Anytown", country="USA", state="CA", zip="12345"),
            email="john.doe@example.com",
            dob="1990-01-01",
            payment_methods={
                "certificate_7815826": Certificate(source="certificate", id="certificate_7815826", amount=100.0),
                "gift_card_7815826": GiftCard(source="gift_card", id="gift_card_7815826", amount=50.0)
            },
            saved_passengers=[],
            membership="regular",
            reservations=["ZFA04Y"]
        )

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "user_123" else None

        guard_payment_methods_are_pre_authorized(
            history=history,
            api=api,
            reservation_id="ZFA04Y",
            total_baggages=2,
            nonfree_baggages=1,
            payment_id="certificate_7815826,gift_card_7815826"
        )

    def test_four_gift_cards(self):
        """
        Policy: "Payment Methods Are Pre-Authorized"
        Example: "An agent submits an UpdateReservationBaggages request using four gift cards for payment."
        """
        
        history = MagicMock()
        history.ask_bool.return_value = True

        user = User(
            user_id="user_123",
            name=Name(first_name="John", last_name="Doe"),
            address=Address(address1="123 Main St", address2=None, city="Anytown", country="USA", state="CA", zip="12345"),
            email="john.doe@example.com",
            dob="1990-01-01",
            payment_methods={
                "gift_card_7815826": GiftCard(source="gift_card", id="gift_card_7815826", amount=50.0),
                "gift_card_7815827": GiftCard(source="gift_card", id="gift_card_7815827", amount=50.0),
                "gift_card_7815828": GiftCard(source="gift_card", id="gift_card_7815828", amount=50.0),
                "gift_card_7815829": GiftCard(source="gift_card", id="gift_card_7815829", amount=50.0)
            },
            saved_passengers=[],
            membership="regular",
            reservations=["ZFA04Y"]
        )

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "user_123" else None

        with pytest.raises(PolicyViolationException):
            guard_payment_methods_are_pre_authorized(
                history=history,
                api=api,
                reservation_id="ZFA04Y",
                total_baggages=2,
                nonfree_baggages=1,
                payment_id="gift_card_7815826,gift_card_7815827,gift_card_7815828,gift_card_7815829"
            )
