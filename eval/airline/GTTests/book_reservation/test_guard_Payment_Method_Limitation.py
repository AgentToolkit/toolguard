import unittest
from unittest.mock import MagicMock, patch

# Importing necessary modules from the application
from my_app.book_reservation.guard_book_reservation import guard_book_reservation
from my_app.common import *
from my_app.domain import *

class TestPaymentMethodLimitationCompliance(unittest.TestCase):
    
    def setUp(self):
        # Mocking the chat history
        self.history = MagicMock()
        self.history.ask_bool.return_value = True

        # Mocking the FlightBookingApi
        self.api = MagicMock()
        self.api.get_flight_on_date_details.return_value = GetFlightOnDateDetailsResponse.model_construct(
            status="available",
            available_seats=AvailableSeats.model_construct(
                basic_economy= 9,
                economy= 9,
                business= 9
            ),
            prices=Prices.model_construct(
                basic_economy= 900,
                economy= 9,
                business= 9
            )
        )

    def test_compliance_one_credit_card(self):
        """The user books a flight using one credit card and two gift cards, all listed in their profile, adhering to the payment method limitation policy."""
        user_details = GetUserDetailsResponse.model_construct(
            payment_methods={
                'credit_card_7815826': PaymentMethods(source='credit_card', brand='Visa', last_four='1234'),
            },
            membership="gold")
        self.api.get_user_details.return_value = user_details

        args = BookReservationRequest(
            user_id='sara_doe_496',
            origin='SFO',
            destination='JFK',
            flight_type='one_way',
            cabin='economy',
            flights=[Flight(flight_number='HAT001', date='2024-05-01')],
            passengers=[Passenger(first_name='Noah', last_name='Brown', dob='1990-01-01')],
            payment_methods=[
                PaymentMethod(payment_id='credit_card_7815826', amount=200)
            ],
            total_baggages=2,
            nonfree_baggages=1,
            insurance='yes'
        )

        # Invoke the function under test
        guard_book_reservation(args, self.history, self.api)

    def test_compliance_one_credit_card_two_gift_cards(self):
        """The user books a flight using one credit card and two gift cards, all listed in their profile, adhering to the payment method limitation policy."""
        user_details = GetUserDetailsResponse.model_construct(payment_methods={
            'credit_card_7815826': PaymentMethods(source='credit_card', brand='Visa', last_four='1234'),
            'gift_card_7815826': PaymentMethods(source='gift_card', amount=50),
            'gift_card_7815827': PaymentMethods(source='gift_card', amount=75)
        },
        membership="gold")
        self.api.get_user_details.return_value = user_details

        args = BookReservationRequest(
            user_id='sara_doe_496',
            origin='SFO',
            destination='JFK',
            flight_type='one_way',
            cabin='economy',
            flights=[Flight(flight_number='HAT001', date='2024-05-01')],
            passengers=[Passenger(first_name='Noah', last_name='Brown', dob='1990-01-01')],
            payment_methods=[
                PaymentMethod(payment_id='credit_card_7815826', amount=200),
                PaymentMethod(payment_id='gift_card_7815826', amount=50),
                PaymentMethod(payment_id='gift_card_7815827', amount=75)
            ],
            total_baggages=2,
            nonfree_baggages=1,
            insurance='yes'
        )

        # Invoke the function under test
        guard_book_reservation(args, self.history, self.api)


    def test_violation_two_credit_cards_one_gift_card(self):
        """The user books a flight using one credit card and two gift cards, all listed in their profile, adhering to the payment method limitation policy."""
        user_details = GetUserDetailsResponse.model_construct(payment_methods={
            'credit_card_7815826': PaymentMethods(source='credit_card', brand='Visa', last_four='1234'),
            'credit_card_12': PaymentMethods(source='credit_card', brand='Visa', last_four='1234'),
            'gift_card_7815826': PaymentMethods(source='gift_card', amount=50),
            'gift_card_7815827': PaymentMethods(source='gift_card', amount=75)
        })
        self.api.get_user_details.return_value = user_details

        args = BookReservationRequest(
            user_id='sara_doe_496',
            origin='SFO',
            destination='JFK',
            flight_type='one_way',
            cabin='economy',
            flights=[Flight(flight_number='HAT001', date='2024-05-01')],
            passengers=[Passenger(first_name='Noah', last_name='Brown', dob='1990-01-01')],
            payment_methods=[
                PaymentMethod(payment_id='credit_card_7815826', amount=200),
                PaymentMethod(payment_id='gift_card_7815826', amount=50),
                PaymentMethod(payment_id='credit_card_12', amount=75)
            ],
            total_baggages=2,
            nonfree_baggages=1,
            insurance='yes'
        )

    def test_violation_credit_card_not_in_profile(self):
        """A reservation with a credit card not defined in the user profile."""
        user_details = GetUserDetailsResponse.model_construct(payment_methods={
        })
        self.api.get_user_details.return_value = user_details

        args = BookReservationRequest(
            user_id='sara_doe_496',
            origin='SFO',
            destination='JFK',
            flight_type='one_way',
            cabin='economy',
            flights=[Flight(flight_number='HAT001', date='2024-05-01')],
            passengers=[Passenger(first_name='Noah', last_name='Brown', dob='1990-01-01')],
            payment_methods=[
                PaymentMethod(payment_id='credit_card_7815826', amount=200)
            ],
            total_baggages=2,
            nonfree_baggages=1,
            insurance='yes'
        )

        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(args, self.history, self.api)

    def test_violation_gift_card_not_in_profile(self):
        """A reservation with a credit card not defined in the user profile."""
        user_details = GetUserDetailsResponse.model_construct(payment_methods={
        })
        self.api.get_user_details.return_value = user_details

        args = BookReservationRequest(
            user_id='sara_doe_496',
            origin='SFO',
            destination='JFK',
            flight_type='one_way',
            cabin='economy',
            flights=[Flight(flight_number='HAT001', date='2024-05-01')],
            passengers=[Passenger(first_name='Noah', last_name='Brown', dob='1990-01-01')],
            payment_methods=[
                PaymentMethod(payment_id='gift_card_7815826', amount=50),
            ],
            total_baggages=2,
            nonfree_baggages=1,
            insurance='yes'
        )

        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(args, self.history, self.api)

    def test_violation_no_payment_methods(self):
        """A reservation with no payment methods"""

        user_details = GetUserDetailsResponse.model_construct(payment_methods={
            'credit_card_7815826': PaymentMethods(source='credit_card', brand='Visa', last_four='1234'),
            'credit_card_7815827': PaymentMethods(source='credit_card', brand='MasterCard', last_four='5678')
        })
        self.api.get_user_details.return_value = user_details

        args = BookReservationRequest(
            user_id='sara_doe_496',
            origin='SFO',
            destination='JFK',
            flight_type='one_way',
            cabin='economy',
            flights=[Flight(flight_number='HAT001', date='2024-05-01')],
            passengers=[Passenger(first_name='Noah', last_name='Brown', dob='1990-01-01')],
            payment_methods=[  ],
            total_baggages=2,
            nonfree_baggages=1,
            insurance='yes'
        )

        # Expecting PolicyViolationException
        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(args, self.history, self.api)


    def test_violation_two_credit_cards(self):
        """The user attempts to book a flight using two credit cards, violating the limitation of using at most one credit card per reservation."""
        user_details = GetUserDetailsResponse.model_construct(payment_methods={
            'credit_card_7815826': PaymentMethods(source='credit_card', brand='Visa', last_four='1234'),
            'credit_card_7815827': PaymentMethods(source='credit_card', brand='MasterCard', last_four='5678')
        })
        self.api.get_user_details.return_value = user_details

        args = BookReservationRequest(
            user_id='sara_doe_496',
            origin='SFO',
            destination='JFK',
            flight_type='one_way',
            cabin='economy',
            flights=[Flight(flight_number='HAT001', date='2024-05-01')],
            passengers=[Passenger(first_name='Noah', last_name='Brown', dob='1990-01-01')],
            payment_methods=[
                PaymentMethod(payment_id='credit_card_7815826', amount=200),
                PaymentMethod(payment_id='credit_card_7815827', amount=150)
            ],
            total_baggages=2,
            nonfree_baggages=1,
            insurance='yes'
        )

        # Expecting PolicyViolationException
        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(args, self.history, self.api)

    def test_violation_four_gift_cards(self):
        """A user employs four gift cards as payment methods, exceeding the policy's limit of three gift cards per reservation."""
        user_details = GetUserDetailsResponse.model_construct(payment_methods={
            'gift_card_7815826': PaymentMethods(source='gift_card', amount=50),
            'gift_card_7815827': PaymentMethods(source='gift_card', amount=75),
            'gift_card_7815828': PaymentMethods(source='gift_card', amount=100),
            'gift_card_7815829': PaymentMethods(source='gift_card', amount=25)
        })
        self.api.get_user_details.return_value = user_details

        args = BookReservationRequest(
            user_id='sara_doe_496',
            origin='SFO',
            destination='JFK',
            flight_type='one_way',
            cabin='economy',
            flights=[Flight(flight_number='HAT001', date='2024-05-01')],
            passengers=[Passenger(first_name='Noah', last_name='Brown', dob='1990-01-01')],
            payment_methods=[
                PaymentMethod(payment_id='gift_card_7815826', amount=50),
                PaymentMethod(payment_id='gift_card_7815827', amount=75),
                PaymentMethod(payment_id='gift_card_7815828', amount=100),
                PaymentMethod(payment_id='gift_card_7815829', amount=25)
            ],
            total_baggages=2,
            nonfree_baggages=1,
            insurance='yes'
        )

        # Expecting PolicyViolationException
        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(args, self.history, self.api)

    def test_violation_unlisted_payment_method(self):
        """During the booking process, the user tries to use a travel certificate along with a credit card that is not listed in their profile, violating the requirement that payment methods must be pre-listed in the user's profile."""
        user_details = GetUserDetailsResponse.model_construct(payment_methods={
            'certificate_7815826': PaymentMethods(source='certificate', amount=300)
        })
        self.api.get_user_details.return_value = user_details

        args = BookReservationRequest(
            user_id='sara_doe_496',
            origin='SFO',
            destination='JFK',
            flight_type='one_way',
            cabin='economy',
            flights=[Flight(flight_number='HAT001', date='2024-05-01')],
            passengers=[Passenger(first_name='Noah', last_name='Brown', dob='1990-01-01')],
            payment_methods=[
                PaymentMethod(payment_id='certificate_7815826', amount=300),
                PaymentMethod(payment_id='credit_card_7815826', amount=200)
            ],
            total_baggages=2,
            nonfree_baggages=1,
            insurance='yes'
        )

        # Expecting PolicyViolationException
        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(args, self.history, self.api)

    def test_violation_exceeding_gift_card_limit(self):
        """The reservation involves one credit card, one travel certificate, and four gift cards, breaching the policy limits on gift card usage."""
        user_details = GetUserDetailsResponse.model_construct(payment_methods={
            'credit_card_7815826': PaymentMethods(source='credit_card', brand='Visa', last_four='1234'),
            'certificate_7815826': PaymentMethods(source='certificate', amount=300),
            'gift_card_7815826': PaymentMethods(source='gift_card', amount=50),
            'gift_card_7815827': PaymentMethods(source='gift_card', amount=75),
            'gift_card_7815828': PaymentMethods(source='gift_card', amount=100),
            'gift_card_7815829': PaymentMethods(source='gift_card', amount=25)
        })
        self.api.get_user_details.return_value = user_details

        args = BookReservationRequest(
            user_id='sara_doe_496',
            origin='SFO',
            destination='JFK',
            flight_type='one_way',
            cabin='economy',
            flights=[Flight(flight_number='HAT001', date='2024-05-01')],
            passengers=[Passenger(first_name='Noah', last_name='Brown', dob='1990-01-01')],
            payment_methods=[
                PaymentMethod(payment_id='credit_card_7815826', amount=200),
                PaymentMethod(payment_id='certificate_7815826', amount=300),
                PaymentMethod(payment_id='gift_card_7815826', amount=50),
                PaymentMethod(payment_id='gift_card_7815827', amount=75),
                PaymentMethod(payment_id='gift_card_7815828', amount=100),
                PaymentMethod(payment_id='gift_card_7815829', amount=25)
            ],
            total_baggages=2,
            nonfree_baggages=1,
            insurance='yes'
        )

        # Expecting PolicyViolationException
        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(args, self.history, self.api)

    def test_violation_two_travel_certificates(self):
        """The user attempts to use two travel certificates for booking a flight, breaching the rule that allows the use of only one travel certificate per reservation."""
        user_details = GetUserDetailsResponse.model_construct(payment_methods={
            'certificate_7815826': PaymentMethods(source='certificate', amount=300),
            'certificate_7815827': PaymentMethods(source='certificate', amount=150)
        })
        self.api.get_user_details.return_value = user_details

        args = BookReservationRequest(
            user_id='sara_doe_496',
            origin='SFO',
            destination='JFK',
            flight_type='one_way',
            cabin='economy',
            flights=[Flight(flight_number='HAT001', date='2024-05-01')],
            passengers=[Passenger(first_name='Noah', last_name='Brown', dob='1990-01-01')],
            payment_methods=[
                PaymentMethod(payment_id='certificate_7815826', amount=300),
                PaymentMethod(payment_id='certificate_7815827', amount=150)
            ],
            total_baggages=2,
            nonfree_baggages=1,
            insurance='yes'
        )

        # Expecting PolicyViolationException
        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(args, self.history, self.api)

if __name__ == '__main__':
    unittest.main()
