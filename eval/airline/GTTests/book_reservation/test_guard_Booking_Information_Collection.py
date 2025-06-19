import unittest
from unittest.mock import MagicMock, patch

# Importing necessary modules
from my_app.book_reservation.guard_book_reservation import guard_book_reservation
from my_app.common import *
from my_app.domain import *

class TestBookingInformationCollectionCompliance(unittest.TestCase):

    """Tests for compliance with the Booking Information Collection policy."""
    def setUp(self):
        # Mocking the chat history
        self.history = MagicMock()
        self.history.ask_bool.return_value = True

        # Mocking the FlightBookingApi
        self.api = MagicMock()
        self.api.get_flight_on_date_details.return_value = GetFlightOnDateDetailsResponse(
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

    def test_compliance_user_id_trip_type_iata_codes(self):
        user_details = GetUserDetailsResponse.model_construct(
            payment_methods={
                'asas': PaymentMethods(source='credit_card', brand='Visa', last_four='1234'),
            },
            membership = "regular"
        )
        self.api.get_user_details.return_value = user_details

        # Function call arguments
        args = BookReservationRequest(
            user_id='john_doe_123',
            origin='SFO',
            destination='JFK',
            flight_type='one_way',
            cabin='economy',
            flights=[Flight(flight_number="FL123", date="2024-05-01")],
            passengers=[
                Passenger(first_name="John", last_name="Doe", dob="1990-01-01")
            ],
            payment_methods=[
                PaymentMethod(payment_id="asas", amount=39)
            ],
            total_baggages=0,
            nonfree_baggages=0,
            insurance='no'
        )

        guard_book_reservation(args, self.history, self.api)

    def test_violation_missing_user_id(self):
        """
        An agent attempts to book a reservation without collecting the user ID, providing only the origin and destination, resulting in an incomplete reservation request.
        """
        user_details = GetUserDetailsResponse.model_construct()
        self.api.get_user_details.return_value = user_details

        # Function call arguments
        args = BookReservationRequest(
            user_id='',  # Missing user ID
            origin='SFO',
            destination='JFK',
            flight_type='one_way',
            cabin='economy',
            flights=[Flight(flight_number="FL123", date="2024-05-01")],
            passengers=[
                Passenger(first_name="John", last_name="Doe", dob="1990-01-01")
            ],
            payment_methods=[
                PaymentMethod(payment_id="asas", amount=39)
            ],
            total_baggages=0,
            nonfree_baggages=0,
            insurance='no'
        )

        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(args, self.history, self.api)


    def test_violation_missing_trip_type(self):
        """
        The agent does not specify the trip type, whether one-way or round-trip, and proceeds to book a flight with only the user's ID, origin, and destination.
        """
        user_details = GetUserDetailsResponse.model_construct()
        self.api.get_user_details.return_value = user_details

        # Function call arguments
        args = BookReservationRequest.model_construct(
            user_id='john_doe_123',
            origin='SFO',
            destination='JFK',
            flight_type='',  # Missing trip type
            cabin='economy',
            flights=[Flight(flight_number="FL123", date="2024-05-01")],
            passengers=[
                Passenger(first_name="John", last_name="Doe", dob="1990-01-01")
            ],
            payment_methods=[
                PaymentMethod(payment_id="asas", amount=39)
            ],
            total_baggages=0,
            nonfree_baggages=0,
            insurance='no'
        )

        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(args, self.history, self.api)


    def test_violation_missing_origin_iata_code(self):
        """
        An agent initiates a reservation with the user_id and destination but forgets to provide the IATA code for the origin, thus failing to comply with the requirement to specify both departure and arrival locations.
        """
        user_details = GetUserDetailsResponse.model_construct()
        self.api.get_user_details.return_value = user_details
        # Function call arguments
        args = BookReservationRequest(
            user_id='john_doe_123',
            origin='',  # Missing origin IATA code
            destination='JFK',
            flight_type='one_way',
            cabin='economy',
            flights=[Flight(flight_number="FL123", date="2024-05-01")],
            passengers=[
                Passenger(first_name="John", last_name="Doe", dob="1990-01-01")
            ],
            payment_methods=[
                PaymentMethod(payment_id="asas", amount=39)
            ],
            total_baggages=0,
            nonfree_baggages=0,
            insurance='no'
        )

        # Invoke function under test and expect exception
        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(args, self.history, self.api)


    def test_violation_non_iata_origin_code(self):
        user_details = GetUserDetailsResponse.model_construct()
        self.api.get_user_details.return_value = user_details

        # Function call arguments
        args = BookReservationRequest(
            user_id='john_doe_123',
            origin='San Francisco',  # Non-IATA origin code
            destination='JFK',
            flight_type='one_way',
            cabin='economy',
            flights=[Flight(flight_number="FL123", date="2024-05-01")],
            passengers=[
                Passenger(first_name="John", last_name="Doe", dob="1990-01-01")
            ],
            payment_methods=[
                PaymentMethod(payment_id="asas", amount=39)
            ],
            total_baggages=0,
            nonfree_baggages=0,
            insurance='no'
        )

        # Invoke function under test and expect exception
        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(args, self.history, self.api)


if __name__ == '__main__':
    unittest.main()
