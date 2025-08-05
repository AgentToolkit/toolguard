import unittest
from unittest.mock import MagicMock
from airline.book_reservation.guard_book_reservation import guard_book_reservation
from airline.common import *
from airline.domain import *

flight = GetFlightInstanceResponse(
    status="available",
    available_seats=AvailableSeats(
        basic_economy= 9,
        economy= 9,
        business= 9
    ),
    prices=Prices(
        basic_economy= 900,
        economy= 9,
        business= 9
    )
)
class TestPassengerInformationRequirementCompliance(unittest.TestCase):
    
    def setUp(self):
        # Mock the history service
        self.history = MagicMock()
        self.history.ask_bool.return_value = True

        # Mock the API
        user = GetUserDetailsResponse(
            name=Name(first_name="Alice", last_name="Smith"),
            email="alice.smith@example.com",
            membership="gold",
            payment_methods={
                'credit_card_123': PaymentMethods(source='credit_card', brand='Visa', last_four='1234'),
            }
        )
        self.api = MagicMock()
        self.api.get_user_details.return_value = user
        self.api.list_all_airports.return_value = ListAllAirportsResponse(root={'JFK': 'JFK AR', 'SFO': 'SFO AR'})
        self.api.search_direct_flight.return_value = []
        self.api.search_onestop_flight.return_value = []
        self.api.get_scheduled_flight.return_value = ""
        self.api.get_reservation_details.return_value = GetReservationDetailsResponse()
        self.api.get_flight_instance.return_value = flight

    # Compliance Tests
    def test_five_passengers_with_complete_information(self):
        """
        Booking a reservation for five passengers, providing first names, last names, and date of births for each. All passengers are scheduled for the same flight and cabin, adhering completely to the policy limit and requirements.
        """
        args = BookReservationRequest(
            user_id="user_123",
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin="economy",
            flights=[Flight(flight_number="FL123", date="2024-05-01")],
            passengers=[
                Passenger(first_name="John", last_name="Doe", dob="1990-01-01"),
                Passenger(first_name="Jane", last_name="Doe", dob="1991-02-02"),
                Passenger(first_name="Jim", last_name="Beam", dob="1992-03-03"),
                Passenger(first_name="Jack", last_name="Daniels", dob="1993-04-04"),
                Passenger(first_name="Jill", last_name="Valentine", dob="1994-05-05")
            ],
            payment_methods=[PaymentMethod(payment_id='credit_card_123', amount=500.0)],
            total_baggages=0,
            nonfree_baggages=0,
            insurance="no"
        )
        # No exception should be raised
        guard_book_reservation(args, self.history, self.api)

    def test_2passaengers_missing_date_of_birth_violation(self):
        """
        Passengers: A reservation with 2 passangers, one of them missing date of birth
        """
        # function call arguments
        passengers = [
            Passenger(first_name="John", last_name="Doe", dob="1990-01-01"),
            Passenger(first_name="Jane", last_name="Smith", dob="")
        ]
        args = BookReservationRequest(
            user_id="user_123",
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin="economy",
            passengers=passengers,
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            flights=[],
            payment_methods=[PaymentMethod(payment_id='credit_card_123', amount=500.0)]
        )

        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(args, self.history, self.api)

    def test_missing_first_name_violation(self):
        """
        Passengers: A reservation with 2 passangers, one of them missing first name
        """
        # function call arguments
        passengers = [
            Passenger(first_name="", last_name="Doe", dob="1990-01-01"),
            Passenger(first_name="Jane", last_name="Smith", dob="1992-02-02")
        ]
        request = BookReservationRequest(
            user_id="user_123",
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin="economy",
            passengers=passengers,
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            flights=[],
            payment_methods=[PaymentMethod(payment_id='credit_card_123', amount=500.0)]
        )

        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(request, self.history, self.api)

    def test_exceeding_passenger_limit_violation(self):
        """
        Passengers: A reservation with 6 passangers
        """
        # function call arguments
        passengers = [
            Passenger(first_name="John", last_name="Doe", dob="1990-01-01"),
            Passenger(first_name="Jane", last_name="Smith", dob="1992-02-02"),
            Passenger(first_name="Alice", last_name="Johnson", dob="1993-03-03"),
            Passenger(first_name="Bob", last_name="Brown", dob="1994-04-04"),
            Passenger(first_name="Charlie", last_name="Davis", dob="1995-05-05"),
            Passenger(first_name="Eve", last_name="Wilson", dob="1996-06-06")
        ]
        request = BookReservationRequest(
            user_id="user_123",
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin="economy",
            passengers=passengers,
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            flights=[],
            payment_methods=[PaymentMethod(payment_id='credit_card_123', amount=500.0)]
        )

        with self.assertRaises(PolicyViolationException):
            guard_book_reservation(request, self.history, self.api)


    def test_single_passenger_with_complete_information(self):
        """
        A reservation successfully made for a single passenger with complete required information: first name, last name, and date of birth, flying in economy class for a one-way trip.
        """
        args = BookReservationRequest(
            user_id="user_123",
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin="economy",
            flights=[Flight(flight_number="FL123", date="2024-05-01")],
            passengers=[
                Passenger(first_name="John", last_name="Doe", dob="1990-01-01")
            ],
            payment_methods=[PaymentMethod(payment_id='credit_card_123', amount=500.0)],
            total_baggages=0,
            nonfree_baggages=0,
            insurance="no"
        )
        # No exception should be raised
        guard_book_reservation(args, self.history, self.api)

    # Violation Tests
    def test_six_passengers_violation(self):
        """
        Attempting to book a reservation with six passengers, violating the policy that allows a maximum of five passengers per reservation.
        """
        args = BookReservationRequest(
            user_id="user_123",
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin="economy",
            flights=[Flight(flight_number="FL123", date="2024-05-01")],
            passengers=[
                Passenger(first_name="John", last_name="Doe", dob="1990-01-01"),
                Passenger(first_name="Jane", last_name="Doe", dob="1991-02-02"),
                Passenger(first_name="Jim", last_name="Beam", dob="1992-03-03"),
                Passenger(first_name="Jack", last_name="Daniels", dob="1993-04-04"),
                Passenger(first_name="Jill", last_name="Valentine", dob="1994-05-05"),
                Passenger(first_name="Jake", last_name="Snake", dob="1995-06-06")
            ],
            payment_methods=[PaymentMethod(payment_id='credit_card_123', amount=500.0)],
            total_baggages=0,
            nonfree_baggages=0,
            insurance="no"
        )
        with self.assertRaises(PolicyViolationException, msg="Expected PolicyViolationException for six passengers, but none was raised."):
            guard_book_reservation(args, self.history, self.api)

    def test_missing_date_of_birth_violation(self):
        """
        Booking a reservation where one passenger is missing their date of birth, violating the requirement that mandates date of birth for each passenger.
        """
        args = BookReservationRequest(
            user_id="user_123",
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin="economy",
            flights=[Flight(flight_number="FL123", date="2024-05-01")],
            passengers=[
                Passenger(first_name="John", last_name="Doe", dob="1990-01-01"),
                Passenger(first_name="Jane", last_name="Doe", dob="1991-02-02"),
                Passenger(first_name="Jim", last_name="Beam", dob="1992-03-03"),
                Passenger(first_name="Jack", last_name="Daniels", dob="1993-04-04"),
                Passenger(first_name="Jill", last_name="Valentine", dob="")
            ],
            payment_methods=[PaymentMethod(payment_id='credit_card_123', amount=500.0)],
            total_baggages=0,
            nonfree_baggages=0,
            insurance="no"
        )
        with self.assertRaises(PolicyViolationException, msg="Expected PolicyViolationException for missing date of birth, but none was raised."):
            guard_book_reservation(args, self.history, self.api)


if __name__ == '__main__':
    unittest.main()
