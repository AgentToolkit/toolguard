import unittest
from unittest.mock import MagicMock, patch

# Importing necessary modules
from my_app.book_reservation.guard_book_reservation import guard_book_reservation
from my_app.common import *
from my_app.domain import *


class TestCheckedBagAllowance(unittest.TestCase):
    def setUp(self):
        # Mocking the chat history
        self.history = MagicMock()
        self.history.ask_bool.return_value = True

        # Mocking the FlightBookingApi
        self.api = MagicMock()
        self.api.get_flight_instance.return_value = GetFlightInstanceResponse(
            status="available",
            available_seats=AvailableSeats(
                basic_economy= 9,
                economy= 9,
                business= 9
            ),
            prices=Prices(
                basic_economy= 900,
                economy= 912,
                business= 649
            )
        )

        self.api.list_all_airports.return_value = ListAllAirportsResponse(root={"SFO": "San Francisco", "JFK": "New York"})

    def test_regular_member_economy_class_one_free_bag(self):
        """A regular member books a reservation in economy class, correctly claiming 1 free checked bag as per policy."""
        # Mocking user details
        user_details = GetUserDetailsResponse(
            payment_methods={
                'asas': PaymentMethods(source='credit_card', brand='Visa', last_four='1234'),
            },
            membership = "regular"
        )
        self.api.get_user_details.return_value = user_details

        # Creating request object
        args = BookReservationRequest(
            user_id='user123',
            origin='SFO',
            destination='JFK',
            flight_type='one_way',
            cabin='economy',
            flights=[Flight(flight_number='FL123', date='2024-05-01')],
            passengers=[Passenger(first_name='John', last_name='Doe', dob='1990-01-01')],
            payment_methods=[PaymentMethod(payment_id='asas', amount=200.0)],
            total_baggages=1,
            nonfree_baggages=0,
            insurance='no'
        )

        guard_book_reservation(args, self.history, self.api)

    def test_regular_member_business_two_bags(self):
        user = GetUserDetailsResponse(
            name=Name(first_name="John", last_name="Doe"),
            email="john.doe@example.com",
            membership="regular",
            payment_methods={
                'credit_card_1234': PaymentMethods(source='credit_card', brand='Visa', last_four='1234'),
            }
        
        )
        self.api.get_user_details.return_value = user

        # Create request
        request = BookReservationRequest(
            user_id="john_doe_123",
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin="business",
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            total_baggages=2,
            nonfree_baggages=0,
            insurance="no",
            flights=[Flight(flight_number="HAT001", date="2024-05-01")],
            payment_methods=[PaymentMethod(payment_id="credit_card_1234", amount=10.0)]
        )

        guard_book_reservation(request, self.history, self.api)

    def test_silver_member_business_three_bags(self):
        """
        A reservation with 1 passenger, in business cabin. The user membership is silver. The reservation contains total 3 bags. The user did not pay for any extra bag
        """

        # Mock the API
        user = GetUserDetailsResponse(
            name=Name(first_name="Jane", last_name="Doe"),
            email="jane.doe@example.com",
            membership="silver",
            payment_methods={
                'credit_card_5678': PaymentMethods(source='credit_card', brand='Visa', last_four='1234'),
            }
        )
        self.api.get_user_details.return_value = user

        # Create request
        request = BookReservationRequest(
            user_id="jane_doe_456",
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin="business",
            passengers=[Passenger(first_name="Jane", last_name="Doe", dob="1992-02-02")],
            total_baggages=3,
            nonfree_baggages=0,
            insurance="no",
            flights=[Flight(flight_number="HAT002", date="2024-05-02")],
            payment_methods=[PaymentMethod(payment_id="credit_card_5678", amount=30.0)]
        )

        guard_book_reservation(request, self.history, self.api)

    def test_gold_member_business_three_bags(self):
        """
        A reservation with 1 passenger, in business cabin. The user membership is gold. The reservation contains total 3 bags. The user did not pay for any extra bag
        """
        user = GetUserDetailsResponse(
            name=Name(first_name="Alice", last_name="Smith"),
            email="alice.smith@example.com",
            membership="gold",
            payment_methods={
                'credit_card_9101': PaymentMethods(source='credit_card', brand='Visa', last_four='1234'),
            }
        )
        self.api.get_user_details.return_value = user

        # Create request
        request = BookReservationRequest(
            user_id="alice_smith_789",
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin="business",
            passengers=[Passenger(first_name="Alice", last_name="Smith", dob="1993-03-03")],
            total_baggages=3,
            nonfree_baggages=0,
            insurance="no",
            flights=[Flight(flight_number="HAT003", date="2024-05-03")],
            payment_methods=[PaymentMethod(payment_id="credit_card_9101", amount=20.0)]
        )

        guard_book_reservation(request, self.history, self.api)


    def test_regular_member_business_three_bags(self):
        """
        A reservation with 1 passenger, in business cabin. The user membership is regular. The reservation contains total 3 bags. The user did not pay for any extra bag
        """
        user = GetUserDetailsResponse(
            name=Name(first_name="Bob", last_name="Brown"),
            email="bob.brown@example.com",
            membership="regular",
            payment_methods={
                'credit_card_1121': PaymentMethods(source='credit_card', brand='Visa', last_four='1234'),
            }
        )
        self.api.get_user_details.return_value = user

        # Create request
        request = BookReservationRequest(
            user_id="bob_brown_321",
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin="business",
            passengers=[Passenger(first_name="Bob", last_name="Brown", dob="1994-04-04")],
            total_baggages=3,
            nonfree_baggages=0,
            insurance="no",
            flights=[Flight(flight_number="HAT004", date="2024-05-04")],
            payment_methods=[PaymentMethod(payment_id="credit_card_1121", amount=0.0)]
        )

        # Invoke function under test
        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(request, self.history, self.api)

    def test_silver_member_business_four_bags(self):
        """
        A reservation with 1 passenger, in business cabin. The user membership is silver. The reservation contains total 4 bags. The user did not pay for any extra bag
        """
        user = GetUserDetailsResponse(
            name=Name(first_name="Charlie", last_name="Davis"),
            email="charlie.davis@example.com",
            membership="silver",
            payment_methods={
                'credit_card_3141': PaymentMethods(source='credit_card', brand='Visa', last_four='1234'),
            }
        )
        self.api.get_user_details.return_value = user

        # Create request
        request = BookReservationRequest(
            user_id="charlie_davis_654",
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin="business",
            passengers=[Passenger(first_name="Charlie", last_name="Davis", dob="1995-05-05")],
            total_baggages=4,
            nonfree_baggages=0,
            insurance="no",
            flights=[Flight(flight_number="HAT005", date="2024-05-05")],
            payment_methods=[PaymentMethod(payment_id="credit_card_3141", amount=0.0)]
        )

        # Invoke function under test
        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(request, self.history, self.api)

    def test_regular_member_business_class_three_free_bags_violation(self):
        """A regular member booking a flight in business class claims 3 free checked bags instead of the allowed 2, resulting in a policy violation."""
        # Mocking user details
        user_details = GetUserDetailsResponse(membership='regular',
            payment_methods={
                'credit_card_123': PaymentMethods(source='credit_card', brand='Visa', last_four='1234'),
            })
        self.api.get_user_details.return_value = user_details

        # Creating request object
        args = BookReservationRequest(
            user_id='user123',
            origin='SFO',
            destination='JFK',
            flight_type='one_way',
            cabin='business',
            flights=[Flight(flight_number='FL123', date='2024-05-01')],
            passengers=[Passenger(first_name='John', last_name='Doe', dob='1990-01-01')],
            payment_methods=[PaymentMethod(payment_id='credit_card_123', amount=200.0)],
            total_baggages=3,
            nonfree_baggages=0,
            insurance='no'
        )

        # Invoke function under test and expect exception
        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(args, self.history, self.api)


# Additional tests for other compliance and violation examples can be added following the same pattern.

if __name__ == '__main__':
    unittest.main()
