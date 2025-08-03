from datetime import datetime, timedelta
import unittest
from unittest.mock import MagicMock, patch

# Importing necessary modules
from airline.update_reservation_passengers.guard_update_reservation_passengers import guard_update_reservation_passengers
from airline.airline_types import *
from airline.i_airline import I_Airline
from rt_toolguard.data_types import PolicyViolationException


class TestGuardObtainUserConfirmationForUpdatingReservationDatabase(unittest.TestCase):

    reservation_id = "ZFA04Y"

    def setUp(self):
        api = MagicMock(spec=I_Airline)
        self.api = api
        reservation = Reservation.model_construct(
            reservation_id=self.reservation_id,
            user_id="user_123",
            origin="SFO",
            destination="JFK",
            flight_type="round_trip",
            cabin="economy",
            flights=[ReservationFlight.model_construct(flight_number="FL123", date="2024-05-01", price=300)],
            passengers=[
                Passenger.model_construct(first_name="JohnNN", last_name="Doe", dob="1990-01-01"),
                Passenger.model_construct(first_name="JohnXX", last_name="Doe", dob="1990-01-01"),
            ],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes"
        )
        api.get_reservation_details.side_effect = lambda r_id: reservation if r_id == reservation.reservation_id else None

        self.history = MagicMock()

    def test_correct_first_name_maintains_passenger_count(self):
        """Updating passenger details for 'reservation_id' 'LMP56O', where a passenger's first name is corrected from 'John' to 'Jon', maintaining the original passenger count of three."""
        # Mocking the API and history
        
        guard_update_reservation_passengers(self.history, self.api,
            reservation_id=self.reservation_id,
            passengers=[
                Passenger.model_construct(first_name="John", last_name="Doe", dob="1990-01-01"),
                Passenger.model_construct(first_name="JohnXX", last_name="Doe", dob="1990-01-01"),
            ],
        )

    def test_add_passenger_violates_policy(self):
        """the update adds a third passenger named Lisa, whereas the reservation initially had two passengers, violating the policy of maintaining the same passenger count."""
        
        with self.assertRaises(PolicyViolationException, msg="Expected PolicyViolationException when adding a passenger."):
            guard_update_reservation_passengers(self.history, self.api,
                reservation_id=self.reservation_id,
                passengers=[
                    Passenger.model_construct(first_name="John", last_name="Doe", dob="1990-01-01"),
                    Passenger.model_construct(first_name="JohnXX", last_name="Doe", dob="1990-01-01"),
                    Passenger.model_construct(first_name="JohnYY", last_name="Doe", dob="1990-01-01"),
                ],
            )

    def test_remove_passenger_violates_policy(self):
        """Attempting to update 'reservation_id' 'DJE45F' by removing a passenger named 'Jonathan White' from the list without replacing him, reducing the count from two to one, which violates the policy requirement."""
        with self.assertRaises(PolicyViolationException, msg="Expected PolicyViolationException when adding a passenger."):
            guard_update_reservation_passengers(self.history, self.api,
                reservation_id=self.reservation_id,
                passengers=[
                    Passenger.model_construct(first_name="John", last_name="Doe", dob="1990-01-01"),
                ],
            )

    def test_update_passenger_dob(self):
        """
        The user requests a correction in the passenger's date of birth.
        """
        guard_update_reservation_passengers(self.history, self.api,
            reservation_id=self.reservation_id,
            passengers=[
                Passenger.model_construct(first_name="John", last_name="Doe", dob="1999-01-01"),
                Passenger.model_construct(first_name="JohnXX", last_name="Doe", dob="1999-01-01"),
            ],
        )
