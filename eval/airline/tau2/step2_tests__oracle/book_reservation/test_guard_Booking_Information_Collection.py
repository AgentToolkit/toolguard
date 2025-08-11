import unittest
from unittest.mock import MagicMock, patch

# Importing necessary modules
from airline.book_reservation.guard_book_reservation import guard_book_reservation
from airline.airline_types import *
from airline.i_airline import I_Airline
from rt_toolguard.data_types import PolicyViolationException

def raise_value_error() -> None:
    raise ValueError("Invalid user_id")

class TestBookingInformationCollectionCompliance(unittest.TestCase):

    user_id = 'regular_user'

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
        ) if flight_number=="FL123" and date=="2024-05-01" else None

        self.api.list_all_airports.return_value = [
            AirportCode.model_construct(iata="SFO", city="San Francisco"),
            AirportCode.model_construct(iata="JFK", city="New York")
        ]

        user = User.model_construct(
            user_id=self.user_id,
            payment_methods={
                'asas': CreditCard(id="asas", source='credit_card', brand='Visa', last_four='1234'),
            },
            membership = "regular"
        )
        self.api.get_user_details.side_effect = lambda user_id: user if user_id == 'regular_user' else raise_value_error()

    def test_compliance_user_id_trip_type_iata_codes(self):

        guard_book_reservation(self.history, self.api, 
            user_id=self.user_id,
            origin='SFO',
            destination='JFK',
            flight_type='one_way',
            cabin='economy',
            flights=[FlightInfo(flight_number="FL123", date="2024-05-01")],
            passengers=[
                Passenger(first_name="John", last_name="Doe", dob="1990-01-01")
            ],
            payment_methods=[
                Payment(payment_id="asas", amount=39)
            ],
            total_baggages=0,
            nonfree_baggages=0,
            insurance='no')

    def test_violation_missing_user_id(self):
        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(self.history, self.api,
                user_id='',  # Missing user ID
                origin='SFO',
                destination='JFK',
                flight_type='one_way',
                cabin='economy',
                flights=[FlightInfo(flight_number="FL123", date="2024-05-01")],
                passengers=[
                    Passenger(first_name="John", last_name="Doe", dob="1990-01-01")
                ],
                payment_methods=[
                    Payment(payment_id="asas", amount=39)
                ],
                total_baggages=0,
                nonfree_baggages=0,
                insurance='no')


    def test_violation_missing_trip_type(self):
        """
        The agent does not specify the trip type, whether one-way or round-trip, and proceeds to book a flight with only the user's ID, origin, and destination.
        """
        
        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(self.history, self.api,
                user_id=self.user_id,
                origin='SFO',
                destination='JFK',
                flight_type='',  # Missing trip type
                cabin='economy',
                flights=[FlightInfo(flight_number="FL123", date="2024-05-01")],
                passengers=[
                    Passenger(first_name="John", last_name="Doe", dob="1990-01-01")
                ],
                payment_methods=[
                    Payment(payment_id="asas", amount=39)
                ],
                total_baggages=0,
                nonfree_baggages=0,
                insurance='no')


    def test_violation_missing_origin_iata_code(self):
        """
        An agent initiates a reservation with the user_id and destination but forgets to provide the IATA code for the origin, thus failing to comply with the requirement to specify both departure and arrival locations.
        """
        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(self.history, self.api,
                user_id=self.user_id,
                origin='',  # Missing origin IATA code
                destination='JFK',
                flight_type='one_way',
                cabin='economy',
                flights=[FlightInfo(flight_number="FL123", date="2024-05-01")],
                passengers=[
                    Passenger(first_name="John", last_name="Doe", dob="1990-01-01")
                ],
                payment_methods=[
                    Payment(payment_id="asas", amount=39)
                ],
                total_baggages=0,
                nonfree_baggages=0,
                insurance='no')


    # def test_violation_non_iata_origin_code(self):
    #     # Invoke function under test and expect exception
    #     with self.assertRaises(PolicyViolationException):
    #         guard_book_reservation(self.history, self.api,
    #             user_id=self.user_id,
    #             origin='San Francisco',  # Non-IATA origin code
    #             destination='JFK',
    #             flight_type='one_way',
    #             cabin='economy',
    #             flights=[FlightInfo(flight_number="FL123", date="2024-05-01")],
    #             passengers=[
    #                 Passenger(first_name="John", last_name="Doe", dob="1990-01-01")
    #             ],
    #             payment_methods=[
    #                 Payment(payment_id="asas", amount=39)
    #             ],
    #             total_baggages=0,
    #             nonfree_baggages=0,
    #             insurance='no')


if __name__ == '__main__':
    unittest.main()
