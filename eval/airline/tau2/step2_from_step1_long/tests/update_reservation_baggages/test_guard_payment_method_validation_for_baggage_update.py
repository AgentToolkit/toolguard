from unittest.mock import MagicMock
import pytest
from datetime import datetime, timedelta
from rt_toolguard.data_types import PolicyViolationException
from airline.update_reservation_baggages.guard_payment_method_validation_for_baggage_update import guard_payment_method_validation_for_baggage_update
from airline.i_airline import I_Airline
from airline.airline_types import User, Name, Address, Reservation, Passenger, Payment, CreditCard, GiftCard, Certificate

class TestGuardPaymentMethodValidationForBaggageUpdate:
    # --- Compliance Examples ---

    def test_update_baggages_with_stored_credit_card(self):
        """
        Policy: Ensure the payment method used is stored in the user's profile before using the 'update_reservation_baggages' tool. Verify the payment method's existence first to maintain transaction security, preventing unauthorized use. This step is crucial for baggage updates.
        Example: A user successfully updates their reservation baggages using a credit card stored in their profile, ensuring secure payment.
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        user_id = "user_123"
        reservation_id = "RES123"
        payment_id = "credit_card_7815826"
        credit_card = CreditCard(source="credit_card", id="credit_card_7815826", brand="visa", last_four="1234")
        user = User(
            user_id=user_id,
            name=Name(first_name="John", last_name="Doe"),
            address=Address(address1="123 Main St", address2=None, city="Metropolis", country="USA", state="NY", zip="10001"),
            email="john.doe@example.com",
            dob="1980-01-01",
            payment_methods={payment_id: credit_card},
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
            cabin="economy",
            flights=[],
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
        # Should not raise
        guard_payment_method_validation_for_baggage_update(history, api, reservation_id, 2, 1, payment_id)

    def test_update_baggages_with_stored_gift_cards(self):
        """
        Policy: Ensure the payment method used is stored in the user's profile before using the 'update_reservation_baggages' tool. Verify the payment method's existence first to maintain transaction security, preventing unauthorized use. This step is crucial for baggage updates.
        Example: The reservation baggages are updated using gift cards stored within the user's profile, complying with the gift card limit.
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        user_id = "user_456"
        reservation_id = "RES456"
        payment_id = "gift_card_111"
        gift_card = GiftCard(source="gift_card", id="gift_card_111", amount=100.0)
        user = User(
            user_id=user_id,
            name=Name(first_name="Jane", last_name="Smith"),
            address=Address(address1="456 Elm St", address2=None, city="Gotham", country="USA", state="CA", zip="90001"),
            email="jane.smith@example.com",
            dob="1990-02-02",
            payment_methods={payment_id: gift_card},
            saved_passengers=[],
            membership="silver",
            reservations=[reservation_id]
        )
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id=user_id,
            origin="LAX",
            destination="ORD",
            flight_type="round_trip",
            cabin="business",
            flights=[],
            passengers=[],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        api.get_user_details.side_effect = lambda uid: user if uid == user_id else None
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        guard_payment_method_validation_for_baggage_update(history, api, reservation_id, 3, 2, payment_id)

    def test_update_baggages_with_stored_certificate(self):
        """
        Policy: Ensure the payment method used is stored in the user's profile before using the 'update_reservation_baggages' tool. Verify the payment method's existence first to maintain transaction security, preventing unauthorized use. This step is crucial for baggage updates.
        Example: A stored travel certificate from the user's profile is utilized to update non-free baggages, aligning with policy requirements.
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        user_id = "user_789"
        reservation_id = "RES789"
        payment_id = "certificate_222"
        certificate = Certificate(source="certificate", id="certificate_222", amount=50.0)
        user = User(
            user_id=user_id,
            name=Name(first_name="Alice", last_name="Wonder"),
            address=Address(address1="789 Oak St", address2=None, city="Star City", country="USA", state="WA", zip="98001"),
            email="alice.wonder@example.com",
            dob="1985-03-03",
            payment_methods={payment_id: certificate},
            saved_passengers=[],
            membership="gold",
            reservations=[reservation_id]
        )
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id=user_id,
            origin="SEA",
            destination="MIA",
            flight_type="one_way",
            cabin="economy",
            flights=[],
            passengers=[],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=0,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        api.get_user_details.side_effect = lambda uid: user if uid == user_id else None
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        guard_payment_method_validation_for_baggage_update(history, api, reservation_id, 1, 1, payment_id)

    def test_update_baggages_with_combination_of_stored_methods(self):
        """
        Policy: Ensure the payment method used is stored in the user's profile before using the 'update_reservation_baggages' tool. Verify the payment method's existence first to maintain transaction security, preventing unauthorized use. This step is crucial for baggage updates.
        Example: Updating the baggage information using a combination of payment methods from the user's profile, adhering to policy limits.
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        user_id = "user_321"
        reservation_id = "RES321"
        payment_id = "gift_card_333"
        gift_card = GiftCard(source="gift_card", id="gift_card_333", amount=75.0)
        credit_card = CreditCard(source="credit_card", id="credit_card_444", brand="mastercard", last_four="5678")
        user = User(
            user_id=user_id,
            name=Name(first_name="Bob", last_name="Builder"),
            address=Address(address1="321 Pine St", address2=None, city="Central City", country="USA", state="IL", zip="60601"),
            email="bob.builder@example.com",
            dob="1975-04-04",
            payment_methods={"gift_card_333": gift_card, "credit_card_444": credit_card},
            saved_passengers=[],
            membership="regular",
            reservations=[reservation_id]
        )
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id=user_id,
            origin="ORD",
            destination="ATL",
            flight_type="round_trip",
            cabin="economy",
            flights=[],
            passengers=[],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=4)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        api.get_user_details.side_effect = lambda uid: user if uid == user_id else None
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        guard_payment_method_validation_for_baggage_update(history, api, reservation_id, 2, 2, payment_id)

    # --- Violation Examples ---

    def test_update_baggages_with_unstored_certificate(self):
        """
        Policy: Ensure the payment method used is stored in the user's profile before using the 'update_reservation_baggages' tool. Verify the payment method's existence first to maintain transaction security, preventing unauthorized use. This step is crucial for baggage updates.
        Example: A user attempts to update their reservation baggages using a certificate or credit card that is not stored in their profile, which leads to transaction insecurity.
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        user_id = "user_654"
        reservation_id = "RES654"
        payment_id = "certificate_999"
        user = User(
            user_id=user_id,
            name=Name(first_name="Eve", last_name="Adams"),
            address=Address(address1="654 Maple St", address2=None, city="Coast City", country="USA", state="FL", zip="33001"),
            email="eve.adams@example.com",
            dob="1995-05-05",
            payment_methods={},  # No certificate_999 in profile
            saved_passengers=[],
            membership="silver",
            reservations=[reservation_id]
        )
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id=user_id,
            origin="MIA",
            destination="SEA",
            flight_type="one_way",
            cabin="business",
            flights=[],
            passengers=[],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=2,
            insurance="no",
            status=None
        )
        api.get_user_details.side_effect = lambda uid: user if uid == user_id else None
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        with pytest.raises(PolicyViolationException):
            guard_payment_method_validation_for_baggage_update(history, api, reservation_id, 3, 3, payment_id)

    def test_update_baggages_with_too_many_gift_cards(self):
        """
        Policy: Ensure the payment method used is stored in the user's profile before using the 'update_reservation_baggages' tool. Verify the payment method's existence first to maintain transaction security, preventing unauthorized use. This step is crucial for baggage updates.
        Example: A user tries to update their reservation baggages using multiple gift cards, exceeding the allowed limit and thus violating payment method constraints.
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        user_id = "user_777"
        reservation_id = "RES777"
        # User has 4 gift cards, exceeding the allowed limit of 3
        payment_methods = {
            "gift_card_1": GiftCard(source="gift_card", id="gift_card_1", amount=25.0),
            "gift_card_2": GiftCard(source="gift_card", id="gift_card_2", amount=25.0),
            "gift_card_3": GiftCard(source="gift_card", id="gift_card_3", amount=25.0),
            "gift_card_4": GiftCard(source="gift_card", id="gift_card_4", amount=25.0),
        }
        user = User(
            user_id=user_id,
            name=Name(first_name="Tom", last_name="Jerry"),
            address=Address(address1="777 Cedar St", address2=None, city="Bludhaven", country="USA", state="NJ", zip="07001"),
            email="tom.jerry@example.com",
            dob="1988-06-06",
            payment_methods=payment_methods,
            saved_passengers=[],
            membership="gold",
            reservations=[reservation_id]
        )
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id=user_id,
            origin="PHL",
            destination="DFW",
            flight_type="round_trip",
            cabin="economy",
            flights=[],
            passengers=[],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=6)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=3,
            nonfree_baggages=3,
            insurance="yes",
            status=None
        )
        api.get_user_details.side_effect = lambda uid: user if uid == user_id else None
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        # Try to use a fourth gift card
        with pytest.raises(PolicyViolationException):
            guard_payment_method_validation_for_baggage_update(history, api, reservation_id, 4, 4, "gift_card_4")

    def test_update_baggages_with_too_many_certificates(self):
        """
        Policy: Ensure the payment method used is stored in the user's profile before using the 'update_reservation_baggages' tool. Verify the payment method's existence first to maintain transaction security, preventing unauthorized use. This step is crucial for baggage updates.
        Example: A user attempts to use a combination of certificates for paying the baggage update, exceeding the allowed limit per reservation.
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        user_id = "user_888"
        reservation_id = "RES888"
        # User has two certificates, but only one allowed per reservation
        payment_methods = {
            "certificate_1": Certificate(source="certificate", id="certificate_1", amount=30.0),
            "certificate_2": Certificate(source="certificate", id="certificate_2", amount=40.0),
        }
        user = User(
            user_id=user_id,
            name=Name(first_name="Clark", last_name="Kent"),
            address=Address(address1="888 Spruce St", address2=None, city="Smallville", country="USA", state="KS", zip="66002"),
            email="clark.kent@example.com",
            dob="1970-07-07",
            payment_methods=payment_methods,
            saved_passengers=[],
            membership="regular",
            reservations=[reservation_id]
        )
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id=user_id,
            origin="DEN",
            destination="BOS",
            flight_type="one_way",
            cabin="business",
            flights=[],
            passengers=[],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=2,
            insurance="no",
            status=None
        )
        api.get_user_details.side_effect = lambda uid: user if uid == user_id else None
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        # Try to use a second certificate
        with pytest.raises(PolicyViolationException):
            guard_payment_method_validation_for_baggage_update(history, api, reservation_id, 3, 3, "certificate_2")
