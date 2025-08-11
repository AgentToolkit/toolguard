import unittest
from unittest.mock import MagicMock, patch

# Importing necessary modules
from airline.book_reservation.guard_book_reservation import guard_book_reservation
from airline.airline_types import *
from airline.i_airline import I_Airline
from rt_toolguard.data_types import PolicyViolationException


class TestCheckedBagAllowance(unittest.TestCase):
    
    regular_user_id = 'regular_user'
    silver_user_id = "silver_user"
    gold_user_id = "gold_user"

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

        silver_user = User.model_construct(
            user_id=self.silver_user_id,
            payment_methods={
                'cc': CreditCard(id="cc", source='credit_card', brand='Visa', last_four='1234'),
            },
            membership = "silver"
        )
        gold_user = User.model_construct(
            user_id=self.gold_user_id,
            payment_methods={
                'cc': CreditCard(id="cc", source='credit_card', brand='Visa', last_four='1234'),
            },
            membership = "gold"
        )
        regular_user = User.model_construct(
            user_id=self.regular_user_id,
            payment_methods={
                'cc': CreditCard(id="cc", source='credit_card', brand='Visa', last_four='1234'),
            },
            membership = "regular"
        )
        users = {
            self.regular_user_id: regular_user,
            self.silver_user_id: silver_user,
            self.gold_user_id: gold_user,
        }
        def get_user_details(u_id):
            if u_id in users:
                return users[u_id]
            raise ValueError
        self.api.get_user_details.side_effect = get_user_details

    def test_regular_member_economy_class_one_free_bag(self):
        
        guard_book_reservation(self.history, self.api,
             user_id = self.regular_user_id,
            origin='SFO',
            destination='JFK',
            flight_type='one_way',
            cabin='economy',
            flights=[FlightInfo(flight_number='FL123', date='2024-05-01')],
            passengers=[Passenger(first_name='John', last_name='Doe', dob='1990-01-01')],
            payment_methods=[Payment(payment_id='cc', amount=200)],
            total_baggages=1,
            nonfree_baggages=0,
            insurance='no')

    def test_regular_member_business_two_bags(self):
        guard_book_reservation(self.history, self.api,
            user_id=self.regular_user_id,
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin="business",
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            total_baggages=2,
            nonfree_baggages=0,
            insurance="no",
            flights=[FlightInfo(flight_number="FL123", date="2024-05-01")],
            payment_methods=[Payment(payment_id="cc", amount=10)]
        )

    def test_silver_member_business_three_bags(self):
        """
        A reservation with 1 passenger, in business cabin. The user membership is silver. The reservation contains total 3 bags. The user did not pay for any extra bag
        """

        guard_book_reservation(self.history, self.api, 
            user_id=self.silver_user_id,
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin="business",
            passengers=[Passenger(first_name="Jane", last_name="Doe", dob="1992-02-02")],
            total_baggages=3,
            nonfree_baggages=0,
            insurance="no",
            flights=[FlightInfo(flight_number="FL123", date="2024-05-01")],
            payment_methods=[Payment(payment_id="cc", amount=30)])

    def test_gold_member_business_three_bags(self):
        """
        A reservation with 1 passenger, in business cabin. The user membership is gold. The reservation contains total 3 bags. The user did not pay for any extra bag
        """

        guard_book_reservation(self.history, self.api,
            user_id=self.gold_user_id,
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin="business",
            passengers=[
                Passenger(first_name="Alice", last_name="Smith", dob="1993-03-03")
            ],
            total_baggages=3,
            nonfree_baggages=0,
            insurance="no",
            flights=[FlightInfo(flight_number="FL123", date="2024-05-01")],
            payment_methods=[Payment(payment_id="cc", amount=20)])


    def test_regular_member_business_three_bags(self):
        """
        A reservation with 1 passenger, in business cabin. The user membership is regular. The reservation contains total 3 bags. The user did not pay for any extra bag
        """
        # Invoke function under test
        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(self.history, self.api,
                user_id=self.regular_user_id,
                origin="SFO",
                destination="JFK",
                flight_type="one_way",
                cabin="business",
                passengers=[Passenger(first_name="Bob", last_name="Brown", dob="1994-04-04")],
                total_baggages=3,
                nonfree_baggages=0,
                insurance="no",
                flights=[FlightInfo(flight_number="FL123", date="2024-05-01")],
                payment_methods=[Payment(payment_id="cc", amount=0)])

    def test_silver_member_business_four_bags(self):
        """
        A reservation with 1 passenger, in business cabin. The user membership is silver. The reservation contains total 4 bags. The user did not pay for any extra bag
        """

        # Invoke function under test
        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(self.history, self.api,
                user_id=self.silver_user_id,
                origin="SFO",
                destination="JFK",
                flight_type="one_way",
                cabin="business",
                passengers=[Passenger(first_name="Charlie", last_name="Davis", dob="1995-05-05")],
                total_baggages=4,
                nonfree_baggages=0,
                insurance="no",
                flights=[FlightInfo(flight_number="FL123", date="2024-05-01")],
                payment_methods=[Payment(payment_id="cc", amount=0)])

    def test_regular_member_business_class_three_free_bags_violation(self):
        """A regular member booking a flight in business class claims 3 free checked bags instead of the allowed 2, resulting in a policy violation."""
        # Mocking user details

        # Invoke function under test and expect exception
        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(self.history, self.api,
            user_id=self.regular_user_id,
            origin='SFO',
            destination='JFK',
            flight_type='one_way',
            cabin='business',
            flights=[FlightInfo(flight_number='FL123', date='2024-05-01')],
            passengers=[Passenger(first_name='John', last_name='Doe', dob='1990-01-01')],
            payment_methods=[Payment(payment_id='cc', amount=200)],
            total_baggages=3,
            nonfree_baggages=0,
            insurance='no')


# Additional tests for other compliance and violation examples can be added following the same pattern.

if __name__ == '__main__':
    unittest.main()
