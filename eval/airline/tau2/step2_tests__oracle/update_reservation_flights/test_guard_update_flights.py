import unittest
from unittest.mock import MagicMock, patch

# Importing necessary modules
from airline.airline_types import *
from airline.i_airline import I_Airline
from airline.update_reservation_flights.guard_update_reservation_flights import guard_update_reservation_flights
from rt_toolguard.data_types import PolicyViolationException

USER = User.model_construct(
    membership = "gold",
    payment_methods={
        'cc': CreditCard(id="cc", source='credit_card', brand='Visa', last_four='1234'),
    },
)
RESERVATIONS = {
    'RSRV1': Reservation.model_construct(
        reservation_id='RSRV1',
        user_id="dav",
        origin='SFO',
        destination='JFK',
        cabin='economy',
        flight_type='round_trip',
        passengers=[
            Passenger(first_name="john", last_name="smith", dob="2000"),
            Passenger(first_name="maria", last_name="smith", dob="1900"),
        ],
        flights=[ReservationFlight.model_construct(flight_number='SFO_JFK', 
                        date='2024-06-01', #change date
                        origin='SFO', destination='JFK')],
        payment_history=[
            Payment(payment_id='cc', amount=123)
        ]
    ),
    'RSRV1BUSINESS': Reservation.model_construct(
        reservation_id='RSRV1',
        user_id="dav",
        origin='SFO',
        destination='JFK',
        cabin='business',
        flight_type='round_trip',
        passengers=[
            Passenger(first_name="john", last_name="smith", dob="2000"),
            Passenger(first_name="maria", last_name="smith", dob="1900"),
        ],
        flights=[ReservationFlight.model_construct(flight_number='SFO_JFK', 
                        date='2024-06-01', #change date
                        origin='SFO', destination='JFK')],
        payment_history=[
            Payment(payment_id='cc', amount=123)
        ]
    ),
    'RSRV2': Reservation.model_construct(
        reservation_id='RSRV2',
        user_id="dav",
        origin='LAX',
        destination='JFK',
        cabin='economy',
        flight_type='round_trip',
        passengers=[
            Passenger(first_name="john", last_name="smith", dob="2000"),
            Passenger(first_name="maria", last_name="smith", dob="1900"),
        ],
        flights=[ReservationFlight.model_construct(flight_number='LAX_JFK', 
                        date='2024-06-01',
                        origin='LAX', destination='JFK')],
        payment_history=[
            Payment(payment_id='cc', amount=123)
        ]
    ),
    'RSRV2LEGS': Reservation.model_construct(
        reservation_id='RSRV2LEGS',
        user_id="dav",
        origin='LAX',
        destination='BLA',
        cabin='economy',
        flight_type='round_trip',
        passengers=[
            Passenger(first_name="john", last_name="smith", dob="2000"),
            Passenger(first_name="maria", last_name="smith", dob="1900"),
        ],
        flights=[ReservationFlight.model_construct(flight_number='LAX_JFK', 
                        date='2024-06-01',
                        origin='LAX', destination='JFK'),
                ReservationFlight.model_construct(flight_number='JFK_BLA', 
                        date='2024-06-01',
                        origin='JFK', destination='BLA')],
        payment_history=[
            Payment(payment_id='cc', amount=123)
        ]
    ),
    'RSRV_BASIC_ECONMY': Reservation.model_construct(
        reservation_id='RSRV_BASIC_ECONMY',
        user_id="dav",
        origin='SFO',
        destination='JFK',
        cabin='basic_economy',
        flight_type='round_trip',
        passengers=[
            Passenger(first_name="john", last_name="smith", dob="2000"),
            Passenger(first_name="maria", last_name="smith", dob="1900"),
        ],
        flights=[ReservationFlight.model_construct(flight_number='SFO_JFK', 
                        date='2024-06-01',
                        origin='SFO', destination='JFK')],
        payment_history=[
            Payment(payment_id='cc', amount=123)
        ]
    )
}

class TestReservationModificationLimitationCompliance(unittest.TestCase):

    def setUp(self):
        self.api = api = MagicMock()
        known_flights = ["SFO_JFK", 'LAX_JFK', 'LAX_BLU', 'BLU_BLA', 'JFK_BLA']

        api.get_user_details.return_value = USER
        api.list_all_airports.return_value = [
            AirportCode.model_construct(iata="SFO", city="San Francisco"),
            AirportCode.model_construct(iata="JFK", city="New York")
        ]
        api.get_reservation_details.side_effect = RESERVATIONS.get
        api.get_flight_status.side_effect = lambda flight_number, date: "available" if flight_number in known_flights and date=="2024-06-01" else None
        
        api.get_scheduled_flight.side_effect = lambda flight_number: Flight.model_construct(
            status="available",
            origin=flight_number.split("_")[0],
            destination=flight_number.split("_")[1],
        )if flight_number in known_flights else None

        api.get_flight_instance.side_effect = lambda flight_number, date: FlightDateStatusAvailable(
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
        )if flight_number in known_flights and date=="2024-06-01" else None


        self.history = MagicMock()
        self.history.ask_bool.return_value = True

    def test_update_reservation_without_changing_origin_destination_trip_type(self):
        """
        An agent updates a reservation while ensuring the origin 'SFO', destination 'JFK', and 'round-trip' type remain unchanged, adhering to policy limitations.
        """

        guard_update_reservation_flights(self.history, self.api, 
            reservation_id='RSRV1',
            cabin='economy',
            flights=[FlightInfo(flight_number='SFO_JFK', date='2024-06-01')],
            payment_id='cc')


    def test_update_reservation_with_wrong_payment(self):
        """
        An agent updates a reservation while ensuring the origin 'SFO', destination 'JFK', and 'round-trip' type remain unchanged, adhering to policy limitations.
        """

        with self.assertRaises(PolicyViolationException):
            guard_update_reservation_flights(self.history, self.api, 
            reservation_id='RSRV1',
            cabin='economy',
            flights=[FlightInfo(flight_number='SFO_JFK', date='2024-06-01')],
            payment_id='weww')


    def test_can_update_connection(self):
        guard_update_reservation_flights(self.history, self.api,
            reservation_id='RSRV2LEGS',
            cabin='economy',
            flights=[
                FlightInfo(flight_number='LAX_BLU', date='2024-06-01'),
                FlightInfo(flight_number='BLU_BLA', date='2024-06-01'),
            ],
            payment_id='cc')

    def test_update_reservation_with_2legs(self):

        guard_update_reservation_flights(self.history, self.api,
            reservation_id='RSRV2LEGS',
            cabin='economy',
            flights=[
                FlightInfo(flight_number='LAX_JFK', date='2024-06-01'),
                FlightInfo(flight_number='JFK_BLA', date='2024-06-01'),
            ],
            payment_id='cc')

    def test_update_business_reservation_without_changing_origin_destination_trip_type(self):
        """
        An agent updates a reservation while ensuring the origin 'SFO', destination 'JFK', and 'round-trip' type remain unchanged, adhering to policy limitations.
        """

        guard_update_reservation_flights(self.history, self.api, 
            reservation_id='RSRV1BUSINESS',
            cabin='business',
            flights=[FlightInfo(flight_number='SFO_JFK', date='2024-06-01')],
            payment_id='cc')

    def test_change_origin_violation(self):
        """
        The agent calls 'update_reservation_flights' to change the origin airport from 'JFK' to 'LAX', violating the policy prohibiting alterations of origin and destination.
        """

        with self.assertRaises(PolicyViolationException):
            guard_update_reservation_flights(self.history, self.api,
            reservation_id='RSRV1',
            cabin='economy',
            flights=[FlightInfo(flight_number='LAX_JFK', date='2024-06-01')],
            payment_id='cc')


    def test_update_basic_economy_reservation(self):
        """
        An agent tries to update a basic-economy reservation
        """

        with self.assertRaises(PolicyViolationException):
            guard_update_reservation_flights(self.history, self.api, 
            reservation_id='RSRV_BASIC_ECONMY',
            cabin='basic_economy',
            flights=[FlightInfo(flight_number='SFO_JFK', date='2024-06-01')],
            payment_id='cc')

    def test_update_to_basic_economy_reservation(self):
        """
        An agent tries to update a basic-economy reservation
        """

        with self.assertRaises(PolicyViolationException):
            guard_update_reservation_flights(self.history, self.api,
            reservation_id='RSRV1',
            cabin='basic_economy',
            flights=[FlightInfo(flight_number='SFO_JFK', date='2024-06-01')],
            payment_id='cc')

    
    def test_update_origin(self):
        """
        An agent tries to update a basic-economy reservation
        """

        with self.assertRaises(PolicyViolationException):
            guard_update_reservation_flights(self.history, self.api,
            reservation_id='RSRV1',
            cabin='basic_economy',
            flights=[FlightInfo(flight_number='LAX_JFK', date='2024-06-01')],
            payment_id='cc')

    def test_update_destination(self):
        """
        An agent tries to update a basic-economy reservation
        """

        with self.assertRaises(PolicyViolationException):
            guard_update_reservation_flights(self.history, self.api,
            reservation_id='RSRV1',
            cabin='basic_economy',
            flights=[FlightInfo(flight_number='JFK_BLA', date='2024-06-01')],
            payment_id='cc')

if __name__ == '__main__':
    unittest.main()
