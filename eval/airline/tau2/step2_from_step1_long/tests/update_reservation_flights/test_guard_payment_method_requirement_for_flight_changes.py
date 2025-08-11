from unittest.mock import MagicMock
import pytest
from datetime import datetime, timedelta
from rt_toolguard.data_types import PolicyViolationException
from airline.update_reservation_flights.guard_payment_method_requirement_for_flight_changes import guard_payment_method_requirement_for_flight_changes
from airline.i_airline import I_Airline
from airline.airline_types import *

class TestGuardPaymentMethodRequirementForFlightChanges:
    # --- Compliance Examples ---

    def test_valid_credit_card_provided(self):
        """
        Policy: "Whenever flights in a reservation are changed, ensure the user provides one valid gift card or credit card from their profile as the payment or refund method. Without this, flight changes cannot be processed."
        Example: "The user requests a flight change and provides a valid credit card from their profile, satisfying the policy requirement for payment method."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        reservation_id = "ZFA04Y"
        user_id = "user_123"
        payment_id = "credit_card_7815826"
        cabin = "economy"
        flights = [FlightInfo(flight_number="HAT001", date="2024-07-01")]
        # Mock user with valid credit card
        user = User(
            user_id=user_id,
            name=Name(first_name="John", last_name="Doe"),
            address=Address(address1="123 Main St", address2=None, city="NYC", country="USA", state="NY", zip="10001"),
            email="john.doe@example.com",
            dob="1990-01-01",
            payment_methods={
                payment_id: CreditCard(source="credit_card", id=payment_id, brand="visa", last_four="1234")
            },
            saved_passengers=[],
            membership="regular",
            reservations=[reservation_id]
        )
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id=user_id,
            origin="JFK",
            destination="LAX",
            flight_type="one_way",
            cabin=cabin,
            flights=[ReservationFlight(flight_number="HAT001", origin="JFK", destination="LAX", date="2024-07-01", price=300)],
            passengers=[],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        api.get_user_details.side_effect = lambda uid: user if uid == user_id else None
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        # Should not raise
        try:
            guard_payment_method_requirement_for_flight_changes(history, api, reservation_id, cabin, flights, payment_id)
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: Expected compliance, but got PolicyViolationException: {e}")

    def test_valid_gift_card_provided(self):
        """
        Policy: "Whenever flights in a reservation are changed, ensure the user provides one valid gift card or credit card from their profile as the payment or refund method. Without this, flight changes cannot be processed."
        Example: "Flight changes are applied after the user selects a valid gift card from their profile for payment, in line with the policy."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        reservation_id = "ZFA04Y"
        user_id = "user_456"
        payment_id = "gift_card_123456"
        cabin = "business"
        flights = [FlightInfo(flight_number="HAT002", date="2024-08-01")]
        user = User(
            user_id=user_id,
            name=Name(first_name="Jane", last_name="Smith"),
            address=Address(address1="456 Elm St", address2=None, city="LA", country="USA", state="CA", zip="90001"),
            email="jane.smith@example.com",
            dob="1985-05-05",
            payment_methods={
                payment_id: GiftCard(source="gift_card", id=payment_id, amount=200.0)
            },
            saved_passengers=[],
            membership="gold",
            reservations=[reservation_id]
        )
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id=user_id,
            origin="LAX",
            destination="JFK",
            flight_type="round_trip",
            cabin=cabin,
            flights=[ReservationFlight(flight_number="HAT002", origin="LAX", destination="JFK", date="2024-08-01", price=500)],
            passengers=[],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        api.get_user_details.side_effect = lambda uid: user if uid == user_id else None
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        try:
            guard_payment_method_requirement_for_flight_changes(history, api, reservation_id, cabin, flights, payment_id)
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: Expected compliance, but got PolicyViolationException: {e}")

    def test_valid_credit_card_linked_to_profile(self):
        """
        Policy: "Whenever flights in a reservation are changed, ensure the user provides one valid gift card or credit card from their profile as the payment or refund method. Without this, flight changes cannot be processed."
        Example: "Users update their flight details and use a valid credit card linked to their profile for payment, fully complying with the policy guidelines."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        reservation_id = "ZFA04Y"
        user_id = "user_789"
        payment_id = "credit_card_999999"
        cabin = "basic_economy"
        flights = [FlightInfo(flight_number="HAT003", date="2024-09-01")]
        user = User(
            user_id=user_id,
            name=Name(first_name="Alice", last_name="Brown"),
            address=Address(address1="789 Oak St", address2=None, city="Chicago", country="USA", state="IL", zip="60601"),
            email="alice.brown@example.com",
            dob="1995-09-09",
            payment_methods={
                payment_id: CreditCard(source="credit_card", id=payment_id, brand="mastercard", last_four="5678")
            },
            saved_passengers=[],
            membership="silver",
            reservations=[reservation_id]
        )
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id=user_id,
            origin="ORD",
            destination="MIA",
            flight_type="one_way",
            cabin=cabin,
            flights=[ReservationFlight(flight_number="HAT003", origin="ORD", destination="MIA", date="2024-09-01", price=400)],
            passengers=[],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        api.get_user_details.side_effect = lambda uid: user if uid == user_id else None
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        try:
            guard_payment_method_requirement_for_flight_changes(history, api, reservation_id, cabin, flights, payment_id)
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: Expected compliance, but got PolicyViolationException: {e}")

    # --- Violation Examples ---

    def test_no_valid_payment_method_provided(self):
        """
        Policy: "Whenever flights in a reservation are changed, ensure the user provides one valid gift card or credit card from their profile as the payment or refund method. Without this, flight changes cannot be processed."
        Example: "A user attempts to change flights in a reservation without providing any valid payment information such as a gift card or credit card linked to their profile, which contravenes the policy."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        reservation_id = "ZFA04Y"
        user_id = "user_321"
        payment_id = ""
        cabin = "economy"
        flights = [FlightInfo(flight_number="HAT004", date="2024-10-01")]
        user = User(
            user_id=user_id,
            name=Name(first_name="Bob", last_name="Green"),
            address=Address(address1="321 Pine St", address2=None, city="Boston", country="USA", state="MA", zip="02101"),
            email="bob.green@example.com",
            dob="1980-12-12",
            payment_methods={},
            saved_passengers=[],
            membership="regular",
            reservations=[reservation_id]
        )
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id=user_id,
            origin="BOS",
            destination="SEA",
            flight_type="one_way",
            cabin=cabin,
            flights=[ReservationFlight(flight_number="HAT004", origin="BOS", destination="SEA", date="2024-10-01", price=350)],
            passengers=[],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        api.get_user_details.side_effect = lambda uid: user if uid == user_id else None
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        with pytest.raises(PolicyViolationException):
            guard_payment_method_requirement_for_flight_changes(history, api, reservation_id, cabin, flights, payment_id)

    def test_certificate_only_as_payment(self):
        """
        Policy: "Whenever flights in a reservation are changed, ensure the user provides one valid gift card or credit card from their profile as the payment or refund method. Without this, flight changes cannot be processed."
        Example: "A flight update process begins with the user providing only a certificate as payment, despite the requirement for a gift card or credit card."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        reservation_id = "ZFA04Y"
        user_id = "user_654"
        payment_id = "certificate_654321"
        cabin = "business"
        flights = [FlightInfo(flight_number="HAT005", date="2024-11-01")]
        user = User(
            user_id=user_id,
            name=Name(first_name="Carol", last_name="White"),
            address=Address(address1="654 Maple St", address2=None, city="Houston", country="USA", state="TX", zip="77001"),
            email="carol.white@example.com",
            dob="1975-03-03",
            payment_methods={
                payment_id: Certificate(source="certificate", id=payment_id, amount=100.0)
            },
            saved_passengers=[],
            membership="silver",
            reservations=[reservation_id]
        )
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id=user_id,
            origin="IAH",
            destination="ATL",
            flight_type="round_trip",
            cabin=cabin,
            flights=[ReservationFlight(flight_number="HAT005", origin="IAH", destination="ATL", date="2024-11-01", price=600)],
            passengers=[],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        api.get_user_details.side_effect = lambda uid: user if uid == user_id else None
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        with pytest.raises(PolicyViolationException):
            guard_payment_method_requirement_for_flight_changes(history, api, reservation_id, cabin, flights, payment_id)

    def test_no_payment_method_selected(self):
        """
        Policy: "Whenever flights in a reservation are changed, ensure the user provides one valid gift card or credit card from their profile as the payment or refund method. Without this, flight changes cannot be processed."
        Example: "Whilst trying to modify their flight itinerary, the user neglects to choose any valid payment method from their profile, which violates the mandatory payment method requirement."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        reservation_id = "ZFA04Y"
        user_id = "user_987"
        payment_id = None
        cabin = "economy"
        flights = [FlightInfo(flight_number="HAT006", date="2024-12-01")]
        user = User(
            user_id=user_id,
            name=Name(first_name="David", last_name="Black"),
            address=Address(address1="987 Cedar St", address2=None, city="Miami", country="USA", state="FL", zip="33101"),
            email="david.black@example.com",
            dob="1992-07-07",
            payment_methods={},
            saved_passengers=[],
            membership="gold",
            reservations=[reservation_id]
        )
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id=user_id,
            origin="MIA",
            destination="ORD",
            flight_type="one_way",
            cabin=cabin,
            flights=[ReservationFlight(flight_number="HAT006", origin="MIA", destination="ORD", date="2024-12-01", price=450)],
            passengers=[],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=4)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        api.get_user_details.side_effect = lambda uid: user if uid == user_id else None
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        with pytest.raises(PolicyViolationException):
            guard_payment_method_requirement_for_flight_changes(history, api, reservation_id, cabin, flights, payment_id)

    def test_payment_method_not_linked_to_profile(self):
        """
        Policy: "Whenever flights in a reservation are changed, ensure the user provides one valid gift card or credit card from their profile as the payment or refund method. Without this, flight changes cannot be processed."
        Example: "A user insists on using a payment method not linked to their profile, such as a friend's credit card, defying the policy's requirement for payment methods to be from the user's profile."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        reservation_id = "ZFA04Y"
        user_id = "user_111"
        payment_id = "credit_card_000000"
        cabin = "business"
        flights = [FlightInfo(flight_number="HAT007", date="2025-01-01")]
        # User has no payment methods matching payment_id
        user = User(
            user_id=user_id,
            name=Name(first_name="Eve", last_name="Gray"),
            address=Address(address1="111 Spruce St", address2=None, city="San Francisco", country="USA", state="CA", zip="94101"),
            email="eve.gray@example.com",
            dob="1988-11-11",
            payment_methods={},
            saved_passengers=[],
            membership="regular",
            reservations=[reservation_id]
        )
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id=user_id,
            origin="SFO",
            destination="LAS",
            flight_type="one_way",
            cabin=cabin,
            flights=[ReservationFlight(flight_number="HAT007", origin="SFO", destination="LAS", date="2025-01-01", price=250)],
            passengers=[],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        api.get_user_details.side_effect = lambda uid: user if uid == user_id else None
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        with pytest.raises(PolicyViolationException):
            guard_payment_method_requirement_for_flight_changes(history, api, reservation_id, cabin, flights, payment_id)
