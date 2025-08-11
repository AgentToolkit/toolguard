from unittest.mock import MagicMock, patch
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.book_reservation.guard_payment_method_restriction import guard_payment_method_restriction
from airline.i_airline import *
from airline.airline_types import *
from datetime import datetime, timedelta

class TestGuardPaymentMethodRestriction:

    def test_single_credit_card_compliance(self):
        """
        Policy: Ensure each reservation uses a maximum of one travel certificate, one credit card, and up to three gift cards.
        Example: A reservation is made using a single credit card that is already registered in the user's profile.
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)

        user = User(
            user_id="sara_doe_496",
            name=Name(first_name="Sara", last_name="Doe"),
            address=Address(address1="123 Main St", address2=None, city="San Francisco", country="USA", state="CA", zip="94105"),
            email="sara.doe@example.com",
            dob="1990-04-05",
            payment_methods={
                "credit_card_1234": CreditCard(source="credit_card", brand="visa", last_four="1234", id="credit_card_1234")
            },
            saved_passengers=[],
            membership="regular",
            reservations=[]
        )

        api.get_user_details.side_effect = lambda user_id: user if user_id == "sara_doe_496" else None

        flights = [FlightInfo(flight_number="HAT001", date="2024-05-01")]
        passengers = [Passenger(first_name="Sara", last_name="Doe", dob="1990-04-05")]
        payment_methods = [CreditCard(source="credit_card", brand="visa", last_four="1234", id="credit_card_1234")]

        try:
            guard_payment_method_restriction(
                history=history,
                api=api,
                user_id="sara_doe_496",
                origin="SFO",
                destination="JFK",
                flight_type="one_way",
                cabin="economy",
                flights=flights,
                passengers=passengers,
                payment_methods=payment_methods,
                total_baggages=1,
                nonfree_baggages=0,
                insurance="no"
            )
        except PolicyViolationException:
            pytest.fail("Unexpected PolicyViolationException raised for compliant payment method.")

    def test_two_credit_cards_violation(self):
        """
        Policy: Ensure each reservation uses a maximum of one travel certificate, one credit card, and up to three gift cards.
        Example: A user attempts to book a reservation using two credit cards.
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)

        user = User(
            user_id="sara_doe_496",
            name=Name(first_name="Sara", last_name="Doe"),
            address=Address(address1="123 Main St", address2=None, city="San Francisco", country="USA", state="CA", zip="94105"),
            email="sara.doe@example.com",
            dob="1990-04-05",
            payment_methods={
                "credit_card_1234": CreditCard(source="credit_card", brand="visa", last_four="1234", id="credit_card_1234"),
                "credit_card_5678": CreditCard(source="credit_card", brand="mastercard", last_four="5678", id="credit_card_5678")
            },
            saved_passengers=[],
            membership="regular",
            reservations=[]
        )

        api.get_user_details.side_effect = lambda user_id: user if user_id == "sara_doe_496" else None

        flights = [FlightInfo(flight_number="HAT001", date="2024-05-01")]
        passengers = [Passenger(first_name="Sara", last_name="Doe", dob="1990-04-05")]
        payment_methods = [
            CreditCard(source="credit_card", brand="visa", last_four="1234", id="credit_card_1234"),
            CreditCard(source="credit_card", brand="mastercard", last_four="5678", id="credit_card_5678")
        ]

        with pytest.raises(PolicyViolationException):
            guard_payment_method_restriction(
                history=history,
                api=api,
                user_id="sara_doe_496",
                origin="SFO",
                destination="JFK",
                flight_type="one_way",
                cabin="economy",
                flights=flights,
                passengers=passengers,
                payment_methods=payment_methods,
                total_baggages=1,
                nonfree_baggages=0,
                insurance="no"
            )

    def test_unregistered_payment_method_violation(self):
        """
        Policy: Verify that all payment methods are pre-registered in the user profile before proceeding with booking.
        Example: A user submits a booking request where the payment method includes a travel certificate not listed in the user profile.
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)

        user = User(
            user_id="sara_doe_496",
            name=Name(first_name="Sara", last_name="Doe"),
            address=Address(address1="123 Main St", address2=None, city="San Francisco", country="USA", state="CA", zip="94105"),
            email="sara.doe@example.com",
            dob="1990-04-05",
            payment_methods={
                "credit_card_1234": CreditCard(source="credit_card", brand="visa", last_four="1234", id="credit_card_1234")
            },
            saved_passengers=[],
            membership="regular",
            reservations=[]
        )

        api.get_user_details.side_effect = lambda user_id: user if user_id == "sara_doe_496" else None

        flights = [FlightInfo(flight_number="HAT001", date="2024-05-01")]
        passengers = [Passenger(first_name="Sara", last_name="Doe", dob="1990-04-05")]
        payment_methods = [
            Certificate(source="certificate", amount=100.0, id="certificate_9999")
        ]

        with pytest.raises(PolicyViolationException):
            guard_payment_method_restriction(
                history=history,
                api=api,
                user_id="sara_doe_496",
                origin="SFO",
                destination="JFK",
                flight_type="one_way",
                cabin="economy",
                flights=flights,
                passengers=passengers,
                payment_methods=payment_methods,
                total_baggages=1,
                nonfree_baggages=0,
                insurance="no"
            )
