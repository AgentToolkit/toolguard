import unittest
from unittest.mock import MagicMock, patch

# Importing the function under test and necessary modules
from airline.book_reservation.guard_book_reservation import guard_book_reservation
from airline.airline_types import *
from airline.i_airline import I_Airline
from rt_toolguard.data_types import PolicyViolationException

class TestConsistentCabinClassPolicy(unittest.TestCase):
    

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
                "economy": 1, #<-last seat
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
            AirportCode.model_construct(iata="JFK", city="New York"),
            AirportCode.model_construct(iata="LAX", city="LAXLAX")
        ]
        gold_user = User.model_construct(
            user_id=self.gold_user_id,
            payment_methods={
                'cc': CreditCard(id="cc", source='credit_card', brand='Visa', last_four='1234'),
            },
            membership = "gold"
        )

        users = {
            self.gold_user_id: gold_user,
        }
        self.api.get_user_details.side_effect = users.get


    def test_1passengers_avail_seats(self):
        """
        Test case for: Maria Gonzalez and Luis Perez both fly economy from LAX to JFK, complying with the consistent cabin class policy.
        """
        guard_book_reservation(self.history, self.api,
            user_id=self.gold_user_id,
            origin='SFO',
            destination='JFK',
            flight_type='one_way',
            cabin='economy',
            flights=[FlightInfo(flight_number='FL123', date='2024-05-01')],
            passengers=[
                Passenger(first_name='Maria', last_name='Gonzalez', dob='1990-01-01')
            ],
            payment_methods=[Payment(payment_id='cc', amount=500)],
            total_baggages=2,
            nonfree_baggages=0,
            insurance='no')

    def test_2passengers_no_avail_seats(self):
        """
        Test case for: Ma§ria Gonzalez and Luis Perez both fly economy from LAX to JFK, complying with the consistent cabin class policy.
        """
        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(self.history, self.api,
                user_id=self.gold_user_id,
                origin='SFO',
                destination='JFK',
                flight_type='one_way',
                cabin='economy',
                flights=[FlightInfo(flight_number='FL123', date='2024-05-01')],
                passengers=[
                    Passenger(first_name='Maria', last_name='Gonzalez', dob='1990-01-01'),
                    Passenger(first_name='Luis', last_name='Perez', dob='1985-05-12')
                ],
                payment_methods=[Payment(payment_id='cc', amount=500.0)],
                total_baggages=2,
                nonfree_baggages=0,
                insurance='no')

if __name__ == '__main__':
    unittest.main()
