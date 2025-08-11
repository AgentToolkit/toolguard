import unittest
from unittest.mock import MagicMock, patch

# Importing necessary modules
from airline.update_reservation_passengers.guard_update_reservation_passengers import guard_update_reservation_passengers
from airline.airline_types import *
from airline.i_airline import I_Airline
from rt_toolguard.data_types import PolicyViolationException


class TestGuardUpdatingPassengers(unittest.TestCase):

    def setUp(self) -> None:
        self.api = api = MagicMock()
        api.get_reservation_details.return_value = Reservation.model_construct(
            reservation_id="LMP56O",
            passengers=[
                Passenger(first_name="John", last_name="Doe", dob="1990-01-01"),
                Passenger(first_name='Jane', last_name='Doe', dob='1992-02-02'),
                Passenger(first_name='Jim', last_name='Beam', dob='1985-05-05')
            ],
            cabin="economy"
        )

        self.history = MagicMock()
        self.history.ask_bool.return_value = True

    def test_update_first_name(self):
        """Updating passenger details for 'reservation_id' 'LMP56O', where a passenger's first name is corrected from 'John' to 'Jon', maintaining the original passenger count of three."""
        guard_update_reservation_passengers(self.history, self.api, 
            reservation_id='LMP56O',
            passengers=[
                Passenger(first_name='Jon', last_name='Doe', dob='1990-01-01'),
                Passenger(first_name='Jane', last_name='Doe', dob='1992-02-02'),
                Passenger(first_name='Jim', last_name='Beam', dob='1985-05-05')
            ])

    def test_update_last_name(self):
        """correcting a passenger's last name spelling from 'Doe' to 'Doer', ensuring the total number of passengers remains unchanged."""
        guard_update_reservation_passengers(self.history, self.api, 
            reservation_id='LMP56O',
            passengers=[
                Passenger(first_name='Jon', last_name='Doer', dob='1990-01-01'),
                Passenger(first_name='Jane', last_name='Doer', dob='1992-02-02'),
                Passenger(first_name='Jim', last_name='Beam', dob='1985-05-05')
            ])
        
    def test_update_dob(self):
        """correcting a passenger's last name spelling from 'Doe' to 'Doer', ensuring the total number of passengers remains unchanged."""
        guard_update_reservation_passengers(self.history, self.api, 
            reservation_id='LMP56O',
            passengers=[
                Passenger(first_name='Jon', last_name='Doe', dob='1890-01-01'),
                Passenger(first_name='Jane', last_name='Doe', dob='1892-02-02'),
                Passenger(first_name='Jim', last_name='Beam', dob='1885-05-05')
            ])

    def test_add_passenger(self):
        """Using 'update_reservation_passengers' for 'reservation_id' '3AB99X', the update adds a third passenger named Lisa, whereas the reservation initially had two passengers, violating the policy of maintaining the same passenger count."""
        with self.assertRaises(PolicyViolationException):
            guard_update_reservation_passengers(self.history, self.api, 
                reservation_id='LMP56O',
                passengers=[
                    Passenger(first_name='Jon', last_name='Doe', dob='1990-01-01'),
                    Passenger(first_name='Jane', last_name='Doe', dob='1992-02-02'),
                    Passenger(first_name='Jim', last_name='Beam', dob='1985-05-05'),
                    Passenger(first_name='yet', last_name='another passenger', dob='1985-05-05')
                ])

    def test_remove_passenger(self):
        """Attempting to update 'reservation_id' 'DJE45F' by removing a passenger named 'Jonathan White' from the list without replacing him, reducing the count from two to one, which violates the policy requirement."""
        with self.assertRaises(PolicyViolationException):
            guard_update_reservation_passengers(self.history, self.api, 
                reservation_id='LMP56O',
                passengers=[
                    Passenger(first_name='Jon', last_name='Doe', dob='1990-01-01'),
                    Passenger(first_name='Jane', last_name='Doe', dob='1992-02-02'),
                ])

if __name__ == '__main__':
    unittest.main()
