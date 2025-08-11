import unittest
from unittest.mock import MagicMock, patch

# Importing necessary modules from the application
from airline.book_reservation.guard_book_reservation import guard_book_reservation
from airline.airline_types import *
from airline.i_airline import I_Airline
from rt_toolguard.data_types import PolicyViolationException

class TestPaymentMethodLimitationCompliance(unittest.TestCase):
    
    regular_user_id = 'regular_user'

    """Tests for compliance with the Booking Information Collection policy."""
    def setUp(self):
        # Mocking the chat history
        self.history = MagicMock()
        self.history.ask_bool.return_value = True

        # Mocking the FlightBookingApi
        self.api = MagicMock()
        self.api.get_flight_status.side_effect = lambda flight_number, date: "available"
        self.api.get_flight_instance.side_effect = lambda flight_number, date: FlightDateStatusAvailable(
            status="available",
            available_seats={
                "basic_economy": 9,
                "economy": 9,
                "business": 9
            },
            prices={
                "basic_economy": 900,
                "economy": 912,
                "business": 649
            }
        )if flight_number=="FL123" and date=="2024-05-01" else None

        self.api.list_all_airports.return_value = [
            AirportCode.model_construct(iata="SFO", city="San Francisco"),
            AirportCode.model_construct(iata="JFK", city="New York")
        ]

        regular_user = User.model_construct(
            user_id=self.regular_user_id,
            payment_methods={
                'cc': CreditCard(id="cc", source='credit_card', brand='Visa', last_four='1234'),
                'cc2': CreditCard(id="cc2", source='credit_card', brand='Visa', last_four='2345'),
                "gc1": GiftCard(id="gc1", amount=2000, source="gift_card"),
                "gc2": GiftCard(id="gc2", amount=2000, source="gift_card"),
                "gc3": GiftCard(id="gc3", amount=2000, source="gift_card"),
                "gc4": GiftCard(id="gc4", amount=2000, source="gift_card"),
                "gc5": GiftCard(id="gc5", amount=2000, source="gift_card"),
                "cert": Certificate(id="cert", amount=2000, source="certificate"),
                "cert2": Certificate(id="cert2", amount=2000, source="certificate"),
            },
            membership = "regular"
        )
        users = {
            self.regular_user_id: regular_user,
        }
        self.api.get_user_details.side_effect = users.get


    def test_compliance_one_credit_card(self):
        """The user books a flight using one credit card and two gift cards, all listed in their profile, adhering to the payment method limitation policy."""

        guard_book_reservation(self.history, self.api,
            user_id=self.regular_user_id,
            origin='SFO',
            destination='JFK',
            flight_type='one_way',
            cabin='economy',
            flights=[FlightInfo(flight_number='FL123', date='2024-05-01')],
            passengers=[Passenger(first_name='Noah', last_name='Brown', dob='1990-01-01')],
            payment_methods=[
                Payment(payment_id='cc', amount=200)
            ],
            total_baggages=2,
            nonfree_baggages=1,
            insurance='yes')
        

    def test_compliance_one_credit_card_two_gift_cards(self):
        """The user books a flight using one credit card and two gift cards, all listed in their profile, adhering to the payment method limitation policy."""
        user_id= 'sara_doe_496'
        user_details = User.model_construct(
            user_id= user_id,
            payment_methods={
                'cc': CreditCard(id="cc", source='credit_card', brand='Visa', last_four='1234'),
                'gift_card_7815826': GiftCard(id="gift_card_7815826", source='gift_card', amount=50),
                'gift_card_7815827': GiftCard(id="gift_card_7815827", source='gift_card', amount=75)
            },
            membership="gold")
        self.api.get_user_details.side_effect = lambda u_id: user_details if u_id == user_id else None

        # Invoke the function under test
        guard_book_reservation(self.history, self.api,
            user_id=user_id,
            origin='SFO',
            destination='JFK',
            flight_type='one_way',
            cabin='basic_economy',
            flights=[FlightInfo(flight_number='FL123', date='2024-05-01')],
            passengers=[Passenger(first_name='Noah', last_name='Brown', dob='1990-01-01')],
            payment_methods=[
                Payment(payment_id='cc', amount=200),
                Payment(payment_id='gift_card_7815826', amount=50),
                Payment(payment_id='gift_card_7815827', amount=75)
            ],
            total_baggages=3,
            nonfree_baggages=1,
            insurance='yes')


    def test_two_credit_cards_one_gift_card(self):
        """The user books a flight using two credit cards and one gift card, all listed in their profile, violating to the payment method limitation policy."""
        with(self.assertRaises(PolicyViolationException)):
            guard_book_reservation(self.history, self.api,
                user_id=self.regular_user_id,
                origin='SFO',
                destination='JFK',
                flight_type='one_way',
                cabin='economy',
                flights=[FlightInfo(flight_number='FL123', date='2024-05-01')],
                passengers=[Passenger(first_name='Noah', last_name='Brown', dob='1990-01-01')],
                payment_methods=[
                    Payment(payment_id='cc', amount=200),
                    Payment(payment_id='gc1', amount=50),
                    Payment(payment_id='cc2', amount=75)
                ],
                total_baggages=2,
                nonfree_baggages=1,
                insurance='yes'
            )

    def test_violation_credit_card_not_in_profile(self):
        """A reservation with a credit card not defined in the user profile."""
        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(self.history, self.api,
                user_id='sara_doe_496',
                origin='SFO',
                destination='JFK',
                flight_type='one_way',
                cabin='economy',
                flights=[FlightInfo(flight_number='FL123', date='2024-05-01')],
                passengers=[Passenger(first_name='Noah', last_name='Brown', dob='1990-01-01')],
                payment_methods=[
                    Payment(payment_id='xxx', amount=200)
                ],
                total_baggages=2,
                nonfree_baggages=1,
                insurance='yes'
            )

    def test_violation_gift_card_not_in_profile(self):
        """A reservation with a credit card not defined in the user profile."""

        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(self.history, self.api,
                user_id='sara_doe_496',
                origin='SFO',
                destination='JFK',
                flight_type='one_way',
                cabin='economy',
                flights=[FlightInfo(flight_number='FL123', date='2024-05-01')],
                passengers=[Passenger(first_name='Noah', last_name='Brown', dob='1990-01-01')],
                payment_methods=[
                    Payment(payment_id='gift_card_7815826', amount=50),
                ],
                total_baggages=2,
                nonfree_baggages=1,
                insurance='yes')

    def test_violation_two_credit_cards(self):
        """The user attempts to book a flight using two credit cards, violating the limitation of using at most one credit card per reservation."""

        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(self.history, self.api,
                user_id=self.regular_user_id,
                origin='SFO',
                destination='JFK',
                flight_type='one_way',
                cabin='economy',
                flights=[FlightInfo(flight_number='FL123', date='2024-05-01')],
                passengers=[Passenger(first_name='Noah', last_name='Brown', dob='1990-01-01')],
                payment_methods=[
                    Payment(payment_id='cc', amount=200),
                    Payment(payment_id='cc2', amount=150)
                ],
                total_baggages=2,
                nonfree_baggages=1,
                insurance='yes')

    def test_violation_four_gift_cards(self):
        """A user employs four gift cards as payment methods, exceeding the policy's limit of three gift cards per reservation."""
        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(self.history, self.api,
                user_id=self.regular_user_id,
                origin='SFO',
                destination='JFK',
                flight_type='one_way',
                cabin='economy',
                flights=[FlightInfo(flight_number='FL123', date='2024-05-01')],
                passengers=[Passenger(first_name='Noah', last_name='Brown', dob='1990-01-01')],
                payment_methods=[
                    Payment(payment_id='gc1', amount=50),
                    Payment(payment_id='gc2', amount=75),
                    Payment(payment_id='gc3', amount=100),
                    Payment(payment_id='gc4', amount=25)
                ],
                total_baggages=2,
                nonfree_baggages=1,
                insurance='yes'
            )

    def test_violation_unlisted_payment_method(self):
        """During the booking process, the user tries to use a travel certificate along with a credit card that is not listed in their profile, violating the requirement that payment methods must be pre-listed in the user's profile."""
        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(self.history, self.api,
                user_id=self.regular_user_id,
                origin='SFO',
                destination='JFK',
                flight_type='one_way',
                cabin='economy',
                flights=[FlightInfo(flight_number='FL123', date='2024-05-01')],
                passengers=[Passenger(first_name='Noah', last_name='Brown', dob='1990-01-01')],
                payment_methods=[
                    Payment(payment_id='certxxx', amount=300),
                    Payment(payment_id='cc', amount=200)
                ],
                total_baggages=2,
                nonfree_baggages=1,
                insurance='yes'
            )

    def test_violation_exceeding_gift_card_limit(self):
        """The reservation involves one credit card, one travel certificate, and four gift cards, breaching the policy limits on gift card usage."""

        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(self.history, self.api,
                user_id=self.regular_user_id,
                origin='SFO',
                destination='JFK',
                flight_type='one_way',
                cabin='economy',
                flights=[FlightInfo(flight_number='FL123', date='2024-05-01')],
                passengers=[Passenger(first_name='Noah', last_name='Brown', dob='1990-01-01')],
                payment_methods=[
                    Payment(payment_id='cc', amount=200),
                    Payment(payment_id='cert', amount=300),
                    Payment(payment_id='gc1', amount=50),
                    Payment(payment_id='gc2', amount=75),
                    Payment(payment_id='gc3', amount=100),
                    Payment(payment_id='gc4', amount=25)
                ],
                total_baggages=2,
                nonfree_baggages=1,
                insurance='yes'
            )

    def test_violation_two_travel_certificates(self):

        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(self.history, self.api,
                user_id=self.regular_user_id,
                origin='SFO',
                destination='JFK',
                flight_type='one_way',
                cabin='economy',
                flights=[FlightInfo(flight_number='FL123', date='2024-05-01')],
                passengers=[Passenger(first_name='Noah', last_name='Brown', dob='1990-01-01')],
                payment_methods=[
                    Payment(payment_id='cert', amount=300),
                    Payment(payment_id='cert2', amount=150)
                ],
                total_baggages=2,
                nonfree_baggages=1,
                insurance='yes'
        )

if __name__ == '__main__':
    unittest.main()
