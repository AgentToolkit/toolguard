from unittest.mock import MagicMock
import pytest
from datetime import datetime, timedelta
from rt_toolguard.data_types import PolicyViolationException
from airline.book_reservation.guard_payment_method_limits_in_booking import guard_payment_method_limits_in_booking
from airline.airline_types import *
from airline.i_airline import *

class TestGuardPaymentMethodLimitsInBooking:
    # --- Compliance Examples ---

    def test_one_certificate_one_credit_two_gift_cards(self):
        """
        Policy: Each reservation can use at most one travel certificate, one credit card, and three gift cards.
        Example: A reservation where the user uses one travel certificate, one credit card, and two gift cards, adhering to the payment method limits.
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        user_id = "user_001"
        # Mock get_user_details to return a user with all payment methods
        api.get_user_details.return_value = User(
            user_id=user_id,
            name=Name(first_name="Sara", last_name="Doe"),
            address=Address(address1="123 Main St", address2=None, city="San Francisco", country="USA", state="CA", zip="94105"),
            email="sara@example.com",
            dob="1990-01-01",
            payment_methods={
                "cert1": Certificate(source="certificate", id="cert1", amount=200.0),
                "cc1": CreditCard(source="credit_card", id="cc1", brand="visa", last_four="1234"),
                "gc1": GiftCard(source="gift_card", id="gc1", amount=50.0),
                "gc2": GiftCard(source="gift_card", id="gc2", amount=30.0),
            },
            saved_passengers=[],
            membership="gold",
            reservations=[]
        )
        payment_methods = [
            Certificate(source="certificate", id="cert1", amount=200.0),
            CreditCard(source="credit_card", id="cc1", brand="visa", last_four="1234"),
            GiftCard(source="gift_card", id="gc1", amount=50.0),
            GiftCard(source="gift_card", id="gc2", amount=30.0),
        ]
        flights = [FlightInfo(flight_number="HAT001", date=datetime.now().strftime("%Y-%m-%d"))]
        passengers = [Passenger(first_name="Sara", last_name="Doe", dob="1990-01-01")]
        guard_payment_method_limits_in_booking(
            history=history,
            api=api,
            user_id=user_id,
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

    def test_one_credit_card_one_gift_card(self):
        """
        Policy: Each reservation can use at most one travel certificate, one credit card, and three gift cards.
        Example: Booking a trip with one credit card and one gift card, complying perfectly with the policy by using no travel certificates.
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        user_id = "user_002"
        api.get_user_details.return_value = User(
            user_id=user_id,
            name=Name(first_name="John", last_name="Smith"),
            address=Address(address1="456 Oak Ave", address2=None, city="New York", country="USA", state="NY", zip="10001"),
            email="john@example.com",
            dob="1985-05-05",
            payment_methods={
                "cc2": CreditCard(source="credit_card", id="cc2", brand="mastercard", last_four="5678"),
                "gc3": GiftCard(source="gift_card", id="gc3", amount=60.0),
            },
            saved_passengers=[],
            membership="regular",
            reservations=[]
        )
        payment_methods = [
            CreditCard(source="credit_card", id="cc2", brand="mastercard", last_four="5678"),
            GiftCard(source="gift_card", id="gc3", amount=60.0),
        ]
        flights = [FlightInfo(flight_number="HAT002", date=datetime.now().strftime("%Y-%m-%d"))]
        passengers = [Passenger(first_name="John", last_name="Smith", dob="1985-05-05")]
        guard_payment_method_limits_in_booking(
            history=history,
            api=api,
            user_id=user_id,
            origin="LAX",
            destination="ORD",
            flight_type="round_trip",
            cabin="business",
            flights=flights,
            passengers=passengers,
            payment_methods=payment_methods,
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes"
        )

    def test_one_certificate_three_gift_cards(self):
        """
        Policy: Each reservation can use at most one travel certificate, one credit card, and three gift cards.
        Example: A booking that utilizes one travel certificate and three gift cards but no credit card, fitting within the acceptable boundaries.
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        user_id = "user_003"
        api.get_user_details.return_value = User(
            user_id=user_id,
            name=Name(first_name="Alice", last_name="Lee"),
            address=Address(address1="789 Pine Rd", address2=None, city="Chicago", country="USA", state="IL", zip="60601"),
            email="alice@example.com",
            dob="1992-07-15",
            payment_methods={
                "cert2": Certificate(source="certificate", id="cert2", amount=150.0),
                "gc4": GiftCard(source="gift_card", id="gc4", amount=40.0),
                "gc5": GiftCard(source="gift_card", id="gc5", amount=25.0),
                "gc6": GiftCard(source="gift_card", id="gc6", amount=35.0),
            },
            saved_passengers=[],
            membership="silver",
            reservations=[]
        )
        payment_methods = [
            Certificate(source="certificate", id="cert2", amount=150.0),
            GiftCard(source="gift_card", id="gc4", amount=40.0),
            GiftCard(source="gift_card", id="gc5", amount=25.0),
            GiftCard(source="gift_card", id="gc6", amount=35.0),
        ]
        flights = [FlightInfo(flight_number="HAT003", date=datetime.now().strftime("%Y-%m-%d"))]
        passengers = [Passenger(first_name="Alice", last_name="Lee", dob="1992-07-15")]
        guard_payment_method_limits_in_booking(
            history=history,
            api=api,
            user_id=user_id,
            origin="ORD",
            destination="MIA",
            flight_type="one_way",
            cabin="basic_economy",
            flights=flights,
            passengers=passengers,
            payment_methods=payment_methods,
            total_baggages=0,
            nonfree_baggages=0,
            insurance="no"
        )

    def test_one_credit_card_only(self):
        """
        Policy: Each reservation can use at most one travel certificate, one credit card, and three gift cards.
        Example: A reservation uses exactly one credit card and no other forms of payment, showing compliance with guidelines.
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        user_id = "user_004"
        api.get_user_details.return_value = User(
            user_id=user_id,
            name=Name(first_name="Bob", last_name="Brown"),
            address=Address(address1="321 Cedar St", address2=None, city="Seattle", country="USA", state="WA", zip="98101"),
            email="bob@example.com",
            dob="1980-12-12",
            payment_methods={
                "cc3": CreditCard(source="credit_card", id="cc3", brand="amex", last_four="4321"),
            },
            saved_passengers=[],
            membership="regular",
            reservations=[]
        )
        payment_methods = [
            CreditCard(source="credit_card", id="cc3", brand="amex", last_four="4321"),
        ]
        flights = [FlightInfo(flight_number="HAT004", date=datetime.now().strftime("%Y-%m-%d"))]
        passengers = [Passenger(first_name="Bob", last_name="Brown", dob="1980-12-12")]
        guard_payment_method_limits_in_booking(
            history=history,
            api=api,
            user_id=user_id,
            origin="SEA",
            destination="DEN",
            flight_type="one_way",
            cabin="economy",
            flights=flights,
            passengers=passengers,
            payment_methods=payment_methods,
            total_baggages=1,
            nonfree_baggages=1,
            insurance="yes"
        )

    def test_one_certificate_two_gift_cards(self):
        """
        Policy: Each reservation can use at most one travel certificate, one credit card, and three gift cards.
        Example: A reservation is booked using one travel certificate, two gift cards, and no credit card. This adheres to the policy's restrictions on payment use by staying within the boundaries for each method.
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        user_id = "user_005"
        api.get_user_details.return_value = User(
            user_id=user_id,
            name=Name(first_name="Eve", last_name="White"),
            address=Address(address1="654 Spruce Ln", address2=None, city="Boston", country="USA", state="MA", zip="02108"),
            email="eve@example.com",
            dob="1995-03-03",
            payment_methods={
                "cert3": Certificate(source="certificate", id="cert3", amount=100.0),
                "gc7": GiftCard(source="gift_card", id="gc7", amount=20.0),
                "gc8": GiftCard(source="gift_card", id="gc8", amount=15.0),
            },
            saved_passengers=[],
            membership="gold",
            reservations=[]
        )
        payment_methods = [
            Certificate(source="certificate", id="cert3", amount=100.0),
            GiftCard(source="gift_card", id="gc7", amount=20.0),
            GiftCard(source="gift_card", id="gc8", amount=15.0),
        ]
        flights = [FlightInfo(flight_number="HAT005", date=datetime.now().strftime("%Y-%m-%d"))]
        passengers = [Passenger(first_name="Eve", last_name="White", dob="1995-03-03")]
        guard_payment_method_limits_in_booking(
            history=history,
            api=api,
            user_id=user_id,
            origin="BOS",
            destination="ATL",
            flight_type="round_trip",
            cabin="business",
            flights=flights,
            passengers=passengers,
            payment_methods=payment_methods,
            total_baggages=2,
            nonfree_baggages=1,
            insurance="no"
        )

    # --- Violation Examples ---

    def test_two_certificates_four_gift_cards_violation(self):
        """
        Policy: Each reservation can use at most one travel certificate, one credit card, and three gift cards.
        Example: A user attempts to book a reservation using two travel certificates and four gift cards, exceeding the policy limits for each of these payment types.
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        user_id = "user_006"
        api.get_user_details.return_value = User(
            user_id=user_id,
            name=Name(first_name="Tom", last_name="Green"),
            address=Address(address1="987 Maple Dr", address2=None, city="Austin", country="USA", state="TX", zip="73301"),
            email="tom@example.com",
            dob="1988-08-08",
            payment_methods={
                "cert4": Certificate(source="certificate", id="cert4", amount=120.0),
                "cert5": Certificate(source="certificate", id="cert5", amount=80.0),
                "gc9": GiftCard(source="gift_card", id="gc9", amount=10.0),
                "gc10": GiftCard(source="gift_card", id="gc10", amount=15.0),
                "gc11": GiftCard(source="gift_card", id="gc11", amount=20.0),
                "gc12": GiftCard(source="gift_card", id="gc12", amount=25.0),
            },
            saved_passengers=[],
            membership="silver",
            reservations=[]
        )
        payment_methods = [
            Certificate(source="certificate", id="cert4", amount=120.0),
            Certificate(source="certificate", id="cert5", amount=80.0),
            GiftCard(source="gift_card", id="gc9", amount=10.0),
            GiftCard(source="gift_card", id="gc10", amount=15.0),
            GiftCard(source="gift_card", id="gc11", amount=20.0),
            GiftCard(source="gift_card", id="gc12", amount=25.0),
        ]
        flights = [FlightInfo(flight_number="HAT006", date=datetime.now().strftime("%Y-%m-%d"))]
        passengers = [Passenger(first_name="Tom", last_name="Green", dob="1988-08-08")]
        with pytest.raises(PolicyViolationException):
            guard_payment_method_limits_in_booking(
                history=history,
                api=api,
                user_id=user_id,
                origin="AUS",
                destination="PHX",
                flight_type="one_way",
                cabin="economy",
                flights=flights,
                passengers=passengers,
                payment_methods=payment_methods,
                total_baggages=1,
                nonfree_baggages=1,
                insurance="no"
            )

    def test_three_credit_cards_violation(self):
        """
        Policy: Each reservation can use at most one travel certificate, one credit card, and three gift cards.
        Example: A reservation is attempted using a combination of three credit cards, violating the policy as only one credit card is permitted per reservation.
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        user_id = "user_007"
        api.get_user_details.return_value = User(
            user_id=user_id,
            name=Name(first_name="Linda", last_name="Black"),
            address=Address(address1="246 Elm St", address2=None, city="Dallas", country="USA", state="TX", zip="75201"),
            email="linda@example.com",
            dob="1975-11-11",
            payment_methods={
                "cc4": CreditCard(source="credit_card", id="cc4", brand="visa", last_four="1111"),
                "cc5": CreditCard(source="credit_card", id="cc5", brand="mastercard", last_four="2222"),
                "cc6": CreditCard(source="credit_card", id="cc6", brand="amex", last_four="3333"),
            },
            saved_passengers=[],
            membership="gold",
            reservations=[]
        )
        payment_methods = [
            CreditCard(source="credit_card", id="cc4", brand="visa", last_four="1111"),
            CreditCard(source="credit_card", id="cc5", brand="mastercard", last_four="2222"),
            CreditCard(source="credit_card", id="cc6", brand="amex", last_four="3333"),
        ]
        flights = [FlightInfo(flight_number="HAT007", date=datetime.now().strftime("%Y-%m-%d"))]
        passengers = [Passenger(first_name="Linda", last_name="Black", dob="1975-11-11")]
        with pytest.raises(PolicyViolationException):
            guard_payment_method_limits_in_booking(
                history=history,
                api=api,
                user_id=user_id,
                origin="DFW",
                destination="LAS",
                flight_type="round_trip",
                cabin="business",
                flights=flights,
                passengers=passengers,
                payment_methods=payment_methods,
                total_baggages=2,
                nonfree_baggages=1,
                insurance="yes"
            )

    def test_one_certificate_four_gift_cards_violation(self):
        """
        Policy: Each reservation can use at most one travel certificate, one credit card, and three gift cards.
        Example: Attempting to book a flight using one travel certificate and four gift cards, which breaches the limit on gift cards.
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        user_id = "user_008"
        api.get_user_details.return_value = User(
            user_id=user_id,
            name=Name(first_name="Sam", last_name="Blue"),
            address=Address(address1="135 Willow Way", address2=None, city="Miami", country="USA", state="FL", zip="33101"),
            email="sam@example.com",
            dob="1993-09-09",
            payment_methods={
                "cert6": Certificate(source="certificate", id="cert6", amount=90.0),
                "gc13": GiftCard(source="gift_card", id="gc13", amount=10.0),
                "gc14": GiftCard(source="gift_card", id="gc14", amount=15.0),
                "gc15": GiftCard(source="gift_card", id="gc15", amount=20.0),
                "gc16": GiftCard(source="gift_card", id="gc16", amount=25.0),
            },
            saved_passengers=[],
            membership="silver",
            reservations=[]
        )
        payment_methods = [
            Certificate(source="certificate", id="cert6", amount=90.0),
            GiftCard(source="gift_card", id="gc13", amount=10.0),
            GiftCard(source="gift_card", id="gc14", amount=15.0),
            GiftCard(source="gift_card", id="gc15", amount=20.0),
            GiftCard(source="gift_card", id="gc16", amount=25.0),
        ]
        flights = [FlightInfo(flight_number="HAT008", date=datetime.now().strftime("%Y-%m-%d"))]
        passengers = [Passenger(first_name="Sam", last_name="Blue", dob="1993-09-09")]
        with pytest.raises(PolicyViolationException):
            guard_payment_method_limits_in_booking(
                history=history,
                api=api,
                user_id=user_id,
                origin="MIA",
                destination="SEA",
                flight_type="one_way",
                cabin="basic_economy",
                flights=flights,
                passengers=passengers,
                payment_methods=payment_methods,
                total_baggages=0,
                nonfree_baggages=0,
                insurance="no"
            )

    def test_two_credit_cards_violation(self):
        """
        Policy: Each reservation can use at most one travel certificate, one credit card, and three gift cards.
        Example: A user uses two credit cards, exceeding the number allowed per reservation.
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        user_id = "user_009"
        api.get_user_details.return_value = User(
            user_id=user_id,
            name=Name(first_name="Nina", last_name="Gray"),
            address=Address(address1="753 Birch Blvd", address2=None, city="Denver", country="USA", state="CO", zip="80202"),
            email="nina@example.com",
            dob="1982-02-02",
            payment_methods={
                "cc7": CreditCard(source="credit_card", id="cc7", brand="visa", last_four="4444"),
                "cc8": CreditCard(source="credit_card", id="cc8", brand="mastercard", last_four="5555"),
            },
            saved_passengers=[],
            membership="gold",
            reservations=[]
        )
        payment_methods = [
            CreditCard(source="credit_card", id="cc7", brand="visa", last_four="4444"),
            CreditCard(source="credit_card", id="cc8", brand="mastercard", last_four="5555"),
        ]
        flights = [FlightInfo(flight_number="HAT009", date=datetime.now().strftime("%Y-%m-%d"))]
        passengers = [Passenger(first_name="Nina", last_name="Gray", dob="1982-02-02")]
        with pytest.raises(PolicyViolationException):
            guard_payment_method_limits_in_booking(
                history=history,
                api=api,
                user_id=user_id,
                origin="DEN",
                destination="BOS",
                flight_type="round_trip",
                cabin="economy",
                flights=flights,
                passengers=passengers,
                payment_methods=payment_methods,
                total_baggages=1,
                nonfree_baggages=1,
                insurance="yes"
            )

    def test_zero_certificates_three_credit_cards_four_gift_cards_violation(self):
        """
        Policy: Each reservation can use at most one travel certificate, one credit card, and three gift cards.
        Example: An attempt is made to book a reservation using zero travel certificates, three credit cards, and four gift cards, violating the restriction on both credit card and gift card quantities.
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        user_id = "user_010"
        api.get_user_details.return_value = User(
            user_id=user_id,
            name=Name(first_name="Oscar", last_name="Red"),
            address=Address(address1="159 Aspen Ct", address2=None, city="Portland", country="USA", state="OR", zip="97201"),
            email="oscar@example.com",
            dob="1970-10-10",
            payment_methods={
                "cc9": CreditCard(source="credit_card", id="cc9", brand="visa", last_four="6666"),
                "cc10": CreditCard(source="credit_card", id="cc10", brand="mastercard", last_four="7777"),
                "cc11": CreditCard(source="credit_card", id="cc11", brand="amex", last_four="8888"),
                "gc17": GiftCard(source="gift_card", id="gc17", amount=10.0),
                "gc18": GiftCard(source="gift_card", id="gc18", amount=15.0),
                "gc19": GiftCard(source="gift_card", id="gc19", amount=20.0),
                "gc20": GiftCard(source="gift_card", id="gc20", amount=25.0),
            },
            saved_passengers=[],
            membership="regular",
            reservations=[]
        )
        payment_methods = [
            CreditCard(source="credit_card", id="cc9", brand="visa", last_four="6666"),
            CreditCard(source="credit_card", id="cc10", brand="mastercard", last_four="7777"),
            CreditCard(source="credit_card", id="cc11", brand="amex", last_four="8888"),
            GiftCard(source="gift_card", id="gc17", amount=10.0),
            GiftCard(source="gift_card", id="gc18", amount=15.0),
            GiftCard(source="gift_card", id="gc19", amount=20.0),
            GiftCard(source="gift_card", id="gc20", amount=25.0),
        ]
        flights = [FlightInfo(flight_number="HAT010", date=datetime.now().strftime("%Y-%m-%d"))]
        passengers = [Passenger(first_name="Oscar", last_name="Red", dob="1970-10-10")]
        with pytest.raises(PolicyViolationException):
            guard_payment_method_limits_in_booking(
                history=history,
                api=api,
                user_id=user_id,
                origin="PDX",
                destination="LAX",
                flight_type="one_way",
                cabin="business",
                flights=flights,
                passengers=passengers,
                payment_methods=payment_methods,
                total_baggages=2,
                nonfree_baggages=2,
                insurance="no"
            )
