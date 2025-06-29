import unittest
from unittest.mock import MagicMock, patch

# Importing the function under test and necessary modules
from my_app.book_reservation.guard_book_reservation import guard_book_reservation
from my_app.common import *
from my_app.domain import *

class TestConsistentCabinClassPolicy(unittest.TestCase):
    
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
                economy= 1, #<-last seat
                business= 9
            ),
            prices=Prices(
                basic_economy= 900,
                economy= 9,
                business= 9
            )
        )
        self.api.get_user_details.return_value = GetUserDetailsResponse(
            name=Name(first_name="Alice", last_name="Smith"),
            email="alice.smith@example.com",
            membership="gold",
            payment_methods={
                'credit_card_123': PaymentMethods(source='credit_card', brand='Visa', last_four='1234'),
            }
        )

        self.api.list_all_airports.return_value = ListAllAirportsResponse(root={
            "SFO": "San Francisco", 
            "JFK": "New York",
            "LAX": "ASASAS"
        })

    def test_1passengers_avail_seats(self):
        """
        Test case for: Maria Gonzalez and Luis Perez both fly economy from LAX to JFK, complying with the consistent cabin class policy.
        """
        # Constructing the request
        args = BookReservationRequest(
            user_id='user_123',
            origin='LAX',
            destination='JFK',
            flight_type='one_way',
            cabin='economy',
            flights=[Flight(flight_number='AA123', date='2024-05-01')],
            passengers=[
                Passenger(first_name='Maria', last_name='Gonzalez', dob='1990-01-01')
            ],
            payment_methods=[PaymentMethod(payment_id='credit_card_123', amount=500.0)],
            total_baggages=2,
            nonfree_baggages=0,
            insurance='no'
        )
        guard_book_reservation(args, self.history, self.api)

    def test_2passengers_no_avail_seats(self):
        """
        Test case for: Ma§ria Gonzalez and Luis Perez both fly economy from LAX to JFK, complying with the consistent cabin class policy.
        """
        # Constructing the request
        args = BookReservationRequest(
            user_id='user_123',
            origin='LAX',
            destination='JFK',
            flight_type='one_way',
            cabin='economy',
            flights=[Flight(flight_number='AA123', date='2024-05-01')],
            passengers=[
                Passenger(first_name='Maria', last_name='Gonzalez', dob='1990-01-01'),
                Passenger(first_name='Luis', last_name='Perez', dob='1985-05-12')
            ],
            payment_methods=[PaymentMethod(payment_id='credit_card_123', amount=500.0)],
            total_baggages=2,
            nonfree_baggages=0,
            insurance='no'
        )
        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(args, self.history, self.api)

if __name__ == '__main__':
    unittest.main()
