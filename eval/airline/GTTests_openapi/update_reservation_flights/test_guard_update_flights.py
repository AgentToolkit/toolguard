import unittest
from unittest.mock import MagicMock, patch

# Importing necessary modules
from airline.common import *
from airline.domain import *
from airline.upodate_reservation_flights.guard_update_reservation_flights import guard_update_reservation_flights

FLIGHTS_IDS = ["SFO_JFK", "JFK_BLA", "LAX_JFK", "LAX_BLU", "BLU_BLA", "JFK_BLA"] 
FLIGHTS = { k: GetScheduledFlightResponse.model_construct(
        flight_number=k,
        origin=k.split("_")[0],
        destination=k.split("_")[1]
    ) for k in FLIGHTS_IDS}

AIRPORTS= {
    "SFO": "San Francisco", 
    "JFK": "New York",
    "BLA":"aete",
    "BLU": "AAD"
}
USER = GetUserDetailsResponse(
    membership = "gold",
    payment_methods={
        'credit_card_7815826': PaymentMethods(source='credit_card', brand='Visa', last_four='1234', amount=2333),
    },
)
RESERVATIONS = {
    'RSRV1': GetReservationDetailsResponse(
        reservation_id='RSRV1',
        user_id="dav",
        origin='SFO',
        destination='JFK',
        cabin='economy',
        flight_type='round_trip',
        passengers=[
            Passenger2(first_name="john", last_name="smith", dob="2000"),
            Passenger2(first_name="maria", last_name="smith", dob="1900"),
        ],
        flights=[Flight3(flight_number='SFO_JFK', 
                        date='2024-06-01', #change date
                        origin='SFO', destination='JFK')],
        payment_history=[
            PaymentHistoryItem2(payment_id='credit_card_7815826', amount=123)
        ]
    ),
    'RSRV1BUSINESS': GetReservationDetailsResponse(
        reservation_id='RSRV1',
        user_id="dav",
        origin='SFO',
        destination='JFK',
        cabin='business',
        flight_type='round_trip',
        passengers=[
            Passenger2(first_name="john", last_name="smith", dob="2000"),
            Passenger2(first_name="maria", last_name="smith", dob="1900"),
        ],
        flights=[Flight3(flight_number='SFO_JFK', 
                        date='2024-06-01', #change date
                        origin='SFO', destination='JFK')],
        payment_history=[
            PaymentHistoryItem2(payment_id='credit_card_7815826', amount=123)
        ]
    ),
    'RSRV2': GetReservationDetailsResponse(
        reservation_id='RSRV2',
        user_id="dav",
        origin='LAX',
        destination='JFK',
        cabin='economy',
        flight_type='round_trip',
        passengers=[
            Passenger2(first_name="john", last_name="smith", dob="2000"),
            Passenger2(first_name="maria", last_name="smith", dob="1900"),
        ],
        flights=[Flight3(flight_number='LAX_JFK', 
                        date='2024-06-01',
                        origin='LAX', destination='JFK')],
        payment_history=[
            PaymentHistoryItem2(payment_id='credit_card_7815826', amount=123)
        ]
    ),
    'RSRV2LEGS': GetReservationDetailsResponse(
        reservation_id='RSRV2LEGS',
        user_id="dav",
        origin='LAX',
        destination='BLA',
        cabin='economy',
        flight_type='round_trip',
        passengers=[
            Passenger2(first_name="john", last_name="smith", dob="2000"),
            Passenger2(first_name="maria", last_name="smith", dob="1900"),
        ],
        flights=[Flight3(flight_number='LAX_JFK', 
                        date='2024-06-01',
                        origin='LAX', destination='JFK'),
                Flight3(flight_number='JFK_BLA', 
                        date='2024-06-01',
                        origin='JFK', destination='BLA')],
        payment_history=[
            PaymentHistoryItem2(payment_id='credit_card_7815826', amount=123)
        ]
    ),
    'RSRV_BASIC_ECONMY': GetReservationDetailsResponse(
        reservation_id='RSRV_BASIC_ECONMY',
        user_id="dav",
        origin='SFO',
        destination='JFK',
        cabin='basic_economy',
        flight_type='round_trip',
        passengers=[
            Passenger2(first_name="john", last_name="smith", dob="2000"),
            Passenger2(first_name="maria", last_name="smith", dob="1900"),
        ],
        flights=[Flight3(flight_number='SFO_JFK', 
                        date='2024-06-01',
                        origin='SFO', destination='JFK')],
        payment_history=[
            PaymentHistoryItem2(payment_id='credit_card_7815826', amount=123)
        ]
    )
}

class TestReservationModificationLimitationCompliance(unittest.TestCase):

    def base_story(self):
        api = MagicMock()

        api.get_user_details.return_value = USER

        # reservation = GetReservationDetailsResponse(
        #     user_id="abc",
        #     total_baggages=1,
        #     nonfree_baggages=1,
        #     cabin=cabin,
        #     payment_history=[
        #         PaymentHistoryItem2(payment_id='credit_card_7815826', amount=123)
        #     ]
        # )
        api.list_all_airports.return_value = ListAllAirportsResponse(root=AIRPORTS)

        def get_flight_side_effect(args, **kwargs):
            return FLIGHTS.get(args.flight_id)
        api.get_scheduled_flight.side_effect = get_flight_side_effect

        api.get_flight_instance.return_value = GetFlightInstanceResponse(
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

        history = MagicMock()
        history.ask_bool.return_value = True

        return history, api

    def test_update_reservation_without_changing_origin_destination_trip_type(self):
        """
        An agent updates a reservation while ensuring the origin 'SFO', destination 'JFK', and 'round-trip' type remain unchanged, adhering to policy limitations.
        """
        history, api = self.base_story()
        api.get_reservation_details.return_value = RESERVATIONS.get('RSRV1')
        args = UpdateReservationFlightsRequest(
            reservation_id='RSRV1',
            cabin='economy',
            flights=[Flight2(flight_number='SFO_JFK', date='2024-06-01')],
            payment_id='credit_card_7815826'
        )
        guard_update_reservation_flights(args, history, api)


    def test_update_reservation_with_wrong_payment(self):
        """
        An agent updates a reservation while ensuring the origin 'SFO', destination 'JFK', and 'round-trip' type remain unchanged, adhering to policy limitations.
        """
        history, api = self.base_story()
        api.get_reservation_details.return_value = RESERVATIONS.get('RSRV1')
        args = UpdateReservationFlightsRequest(
            reservation_id='RSRV1',
            cabin='economy',
            flights=[Flight2(flight_number='SFO_JFK', date='2024-06-01')],
            payment_id='weww'
        )
        with self.assertRaises(PolicyViolationException):
            guard_update_reservation_flights(args, history, api)


    def test_can_update_connection(self):
        history, api = self.base_story()
        api.get_reservation_details.return_value = RESERVATIONS.get('RSRV2LEGS')
        args = UpdateReservationFlightsRequest(
            reservation_id='RSRV2LEGS',
            cabin='economy',
            flights=[
                Flight2(flight_number='LAX_BLU', date='2024-06-01'),
                Flight2(flight_number='BLU_BLA', date='2024-06-01'),
            ],
            payment_id='credit_card_7815826'
        )
        guard_update_reservation_flights(args, history, api)

    def test_update_reservation_with_2legs(self):
        history, api = self.base_story()
        api.get_reservation_details.return_value = RESERVATIONS.get('RSRV2LEGS')
        args = UpdateReservationFlightsRequest(
            reservation_id='RSRV2LEGS',
            cabin='economy',
            flights=[
                Flight2(flight_number='LAX_JFK', date='2024-06-01'),
                Flight2(flight_number='JFK_BLA', date='2024-06-01'),
            ],
            payment_id='credit_card_7815826'
        )
        guard_update_reservation_flights(args, history, api)

    def test_update_business_reservation_without_changing_origin_destination_trip_type(self):
        """
        An agent updates a reservation while ensuring the origin 'SFO', destination 'JFK', and 'round-trip' type remain unchanged, adhering to policy limitations.
        """
        history, api = self.base_story()
        api.get_reservation_details.return_value = RESERVATIONS.get('RSRV1BUSINESS')
        args = UpdateReservationFlightsRequest(
            reservation_id='RSRV1BUSINESS',
            cabin='business',
            flights=[Flight2(flight_number='SFO_JFK', date='2024-06-01')],
            payment_id='credit_card_7815826'
        )
        guard_update_reservation_flights(args, history, api)

    def test_change_destination_violation(self):
        """
        The agent calls 'update_reservation_flights' to change the origin airport from 'JFK' to 'LAX', violating the policy prohibiting alterations of origin and destination.
        """
        history, api = self.base_story()
        api.get_reservation_details.return_value = RESERVATIONS.get('RSRV1')
        args = UpdateReservationFlightsRequest(
            reservation_id='RSRV1',
            cabin='economy',
            flights=[Flight2(flight_number='LAX_JFK', date='2024-06-01')],
            payment_id='credit_card_7815826'
        )

        with self.assertRaises(PolicyViolationException):
            guard_update_reservation_flights(args, history, api)


    def test_update_basic_economy_reservation(self):
        """
        An agent tries to update a basic-economy reservation
        """
        history, api = self.base_story()
        api.get_reservation_details.return_value = RESERVATIONS.get('RSRV_BASIC_ECONMY')
        args = UpdateReservationFlightsRequest(
            reservation_id='RSRV_BASIC_ECONMY',
            cabin='basic_economy',
            flights=[Flight2(flight_number='SFO_JFK', date='2024-06-01')],
            payment_id='credit_card_7815826'
        )
        with self.assertRaises(PolicyViolationException):
            guard_update_reservation_flights(args, history, api)

    def test_update_to_basic_economy_reservation(self):
        """
        An agent tries to update a basic-economy reservation
        """
        history, api = self.base_story()
        api.get_reservation_details.return_value = RESERVATIONS.get('RSRV1')
        args = UpdateReservationFlightsRequest(
            reservation_id='RSRV1',
            cabin='basic_economy',
            flights=[Flight2(flight_number='SFO_JFK', date='2024-06-01')],
            payment_id='credit_card_7815826'
        )
        with self.assertRaises(PolicyViolationException):
            guard_update_reservation_flights(args, history, api)

    
    def test_update_origin(self):
        """
        An agent tries to update a basic-economy reservation
        """
        history, api = self.base_story()
        api.get_reservation_details.return_value = RESERVATIONS.get('RSRV1')
        args = UpdateReservationFlightsRequest(
            reservation_id='RSRV1',
            cabin='basic_economy',
            flights=[Flight2(flight_number='LAX_JFK', date='2024-06-01')],
            payment_id='credit_card_7815826'
        )
        with self.assertRaises(PolicyViolationException):
            guard_update_reservation_flights(args, history, api)

    def test_update_destination(self):
        """
        An agent tries to update a basic-economy reservation
        """
        history, api = self.base_story()
        api.get_reservation_details.return_value = RESERVATIONS.get('RSRV1')
        args = UpdateReservationFlightsRequest(
            reservation_id='RSRV1',
            cabin='basic_economy',
            flights=[Flight2(flight_number='JFK_BLA', date='2024-06-01')],
            payment_id='credit_card_7815826'
        )
        with self.assertRaises(PolicyViolationException):
            guard_update_reservation_flights(args, history, api)

if __name__ == '__main__':
    unittest.main()
