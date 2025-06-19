import unittest
from unittest.mock import MagicMock, patch

# Importing necessary modules
from my_app.update_reservation_passengers.guard_update_reservation_passengers import guard_update_reservation_passengers
from my_app.common import *
from my_app.domain import *


class TestGuardObtainUserConfirmationForUpdatingReservationDatabase(unittest.TestCase):
    
    def test_user_confirms_update_passenger_dob(self):
        """
        The user requests a correction in the passenger's date of birth. The agent summarizes the requested changes and asks for confirmation by saying 'yes' to update the reservation. The user responds with 'yes,' and the agent proceeds with the update.
        """
        api = MagicMock()
        api.get_reservation_details.return_value = GetReservationDetailsResponse.model_construct(
            reservation_id="ZFA04Y",
            passengers=[Passenger2(first_name="John", last_name="Doe", dob="1990-01-01")],
            cabin="economy"
        )

        # Mocking the chat history
        history = MagicMock()
        history.ask_bool.return_value = True  # Mock that user confirmed with 'yes'

        # Constructing the request
        args = UpdateReservationPassengersRequest.model_construct(
            reservation_id="ZFA04Y",
            passengers=[Passenger3(first_name="John", last_name="Doe", dob="1990-01-02")],
            cabin="economy"
        )

        # Call the function under test
        guard_update_reservation_passengers(args, history, api)

    # def test_agent_updates_without_user_confirmation(self):
    #     """
    #     An agent updates passenger details for a reservation without informing the user. The user was neither given a summary of the modifications nor asked for a 'yes' confirmation before the change.
    #     """
    #     api = MagicMock()
    #     api.get_reservation_details.return_value = GetReservationDetailsResponse.model_construct(
    #         reservation_id="ZFA04Y",
    #         passengers=[Passenger2(first_name="John", last_name="Doe", dob="1990-01-01")]
    #     )

    #     # Mocking the chat history
    #     history = MagicMock()
    #     history.ask_bool.return_value = False  # Mock that user did not confirm with 'yes'

    #     # Constructing the request
    #     args = UpdateReservationPassengersRequest.model_construct(
    #         reservation_id="ZFA04Y",
    #         passengers=[Passenger3(first_name="John", last_name="Doe", dob="1990-01-02")]
    #     )

    #     # Call the function under test and expect a PolicyViolationException
    #     with self.assertRaises(PolicyViolationException, msg="Expected PolicyViolationException when user confirmation is not obtained."):
    #         guard_update_reservation_passengers(args, history, api)

    # Additional tests for other compliance and violation examples can be added here


if __name__ == '__main__':
    unittest.main()
