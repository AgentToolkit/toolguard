import unittest
from unittest.mock import MagicMock, patch

# Importing necessary modules
from my_app.update_reservation_passengers.guard_update_reservation_passengers import guard_update_reservation_passengers
from my_app.common import *
from my_app.domain import *


class TestPassengerModificationLimitationCompliance(unittest.TestCase):
    """Test compliance scenarios for Passenger Modification Limitation policy."""

    def test_correct_first_name_maintains_passenger_count(self):
        """Updating passenger details for 'reservation_id' 'LMP56O', where a passenger's first name is corrected from 'John' to 'Jon', maintaining the original passenger count of three."""
        # Mocking the API and history
        api:FlightBookingApi = MagicMock()
        api.get_reservation_details.return_value = GetReservationDetailsResponse.model_construct(
            reservation_id="LMP56O",
            passengers=[
                Passenger2(first_name="John", last_name="Doe", dob="1990-01-01"),
                Passenger2.model_construct(first_name='Jane', last_name='Doe', dob='1992-02-02'),
                Passenger2.model_construct(first_name='Jim', last_name='Beam', dob='1985-05-05')
            ],
            cabin="economy"
        )

        history = MagicMock()
        history.ask_bool.return_value = True

        # Constructing the request
        args = UpdateReservationPassengersRequest.model_construct(
            reservation_id='LMP56O',
            passengers=[
                Passenger3.model_construct(first_name='Jon', last_name='Doe', dob='1990-01-01'),
                Passenger3.model_construct(first_name='Jane', last_name='Doe', dob='1992-02-02'),
                Passenger3.model_construct(first_name='Jim', last_name='Beam', dob='1985-05-05')
            ],
            cabin="economy"
        )

        guard_update_reservation_passengers(args, history, api)

    @patch('my_app.domain.FlightBookingApi')
    def test_correct_last_name_maintains_passenger_count(self, MockApi):
        """Using 'update_reservation_passengers' with 'reservation_id' 'ZXV01Q', correcting a passenger's last name spelling from 'Doe' to 'Doer', ensuring the total number of passengers remains unchanged."""
        # Mocking the API and history
        api:FlightBookingApi = MagicMock()
        api.get_reservation_details.return_value = GetReservationDetailsResponse.model_construct(
            reservation_id="ZXV01Q",
            passengers=[
                Passenger2.model_construct(first_name="John", last_name="Doe", dob="1990-01-01"),
                Passenger2.model_construct(first_name='Jane', last_name='Doe', dob='1992-02-02'),
                Passenger2.model_construct(first_name='Jim', last_name='Beam', dob='1985-05-05')
            ],
            cabin="economy"
        )

        history = MagicMock()
        history.ask_bool.return_value = True

        # Constructing the request
        args = UpdateReservationPassengersRequest.model_construct(
            reservation_id='ZXV01Q',
            passengers=[
                Passenger3.model_construct(first_name='John', last_name='Doer', dob='1990-01-01'),
                Passenger3.model_construct(first_name='Jane', last_name='Doe', dob='1992-02-02'),
                Passenger3.model_construct(first_name='Jim', last_name='Beam', dob='1985-05-05')
            ],
            cabin="economy"
        )

        # Invoking the function under test
        guard_update_reservation_passengers(args, history, api)


class TestPassengerModificationLimitationViolation(unittest.TestCase):
    """Test violation scenarios for Passenger Modification Limitation policy."""

    def test_add_passenger_violates_policy(self):
        """Using 'update_reservation_passengers' for 'reservation_id' '3AB99X', the update adds a third passenger named Lisa, whereas the reservation initially had two passengers, violating the policy of maintaining the same passenger count."""
        # Mocking the API and history
        api = MagicMock()
        api.get_reservation_details.return_value = GetReservationDetailsResponse.model_construct(
            reservation_id="3AB99X",
            passengers=[
                Passenger2.model_construct(first_name="John", last_name="Doe", dob="1990-01-01"),
                Passenger2.model_construct(first_name='Jane', last_name='Doe', dob='1992-02-02')
            ],
            cabin="economy"
        )

        history = MagicMock()
        history.ask_bool.return_value = True

        # Constructing the request
        args = UpdateReservationPassengersRequest.model_construct(
            reservation_id='3AB99X',
            passengers=[
                Passenger3.model_construct(first_name='John', last_name='Doe', dob='1990-01-01'),
                Passenger3.model_construct(first_name='Jane', last_name='Doe', dob='1992-02-02'),
                Passenger3.model_construct(first_name='Lisa', last_name='Smith', dob='1995-05-05')
            ],
            cabin="economy"
        )

        # Invoking the function under test and expecting an exception
        with self.assertRaises(PolicyViolationException, msg="Expected PolicyViolationException when adding a passenger."):
            guard_update_reservation_passengers(args, history, api)

    def test_remove_passenger_violates_policy(self):
        """Attempting to update 'reservation_id' 'DJE45F' by removing a passenger named 'Jonathan White' from the list without replacing him, reducing the count from two to one, which violates the policy requirement."""
        # Mocking the API and history
        api = MagicMock()
        api.get_reservation_details.return_value = GetReservationDetailsResponse.model_construct(
            reservation_id="DJE45F",
            passengers=[
                Passenger2.model_construct(first_name='Jane', last_name='Doe', dob='1992-02-02')
            ],
            cabin="economy"
        )
        history = MagicMock()
        history.ask_bool.return_value = True

        # Constructing the request
        args = UpdateReservationPassengersRequest.model_construct(
            reservation_id='DJE45F',
            passengers=[
                Passenger3.model_construct(first_name="John", last_name="Doe", dob="1990-01-01"),
                Passenger3.model_construct(first_name='Jane', last_name='Doe', dob='1992-02-02')
            ],
            cabin="economy"
        )

        # Invoking the function under test and expecting an exception
        with self.assertRaises(PolicyViolationException, msg="Expected PolicyViolationException when removing a passenger."):
            guard_update_reservation_passengers(args, history, api)


if __name__ == '__main__':
    unittest.main()
