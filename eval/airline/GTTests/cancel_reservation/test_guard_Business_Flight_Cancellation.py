from datetime import datetime, timedelta
import unittest
from unittest.mock import MagicMock, patch

# Importing necessary modules
from my_app.cancel_reservation.guard_cancel_reservation import guard_cancel_reservation
from my_app.common import *
from my_app.domain import *


class TestGuardBusinessFlightCancellation(unittest.TestCase):
    

    # Violation test: Agent cancels without checking flight status
    def test_violation_booked_12h_ago_but_the_flight_landed(self):
        """
        Test case: An agent cancels a reservation without checking if any flight segment has been flown and finds out post-operation that one of the flights was already completed, violating policy requirements.
        """
        args = CancelReservationRequest.model_construct(reservation_id='ZFA04Y')
        history = MagicMock()
        history.ask_bool.return_value = True

        api = MagicMock()
        flight_details = GetFlightOnDateDetailsResponse.model_construct(status='landed')
        api.get_flight_on_date_details.return_value = flight_details
        api.get_reservation_details.return_value = GetReservationDetailsResponse.model_construct(
            flights=[Flight3.model_construct(
                flight_number='LY232',
                date="2025-02-28"
            )],
            created_at=(datetime.now() - timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S")
        )

        with self.assertRaises(PolicyViolationException):
            guard_cancel_reservation(args, history, api)


    
    def test_basic_have_insurance_but_is_flying(self):
        args = CancelReservationRequest.model_construct(reservation_id="ZFA04Y")
        history = MagicMock()
        history.ask_bool.return_value = True

        api = MagicMock()
        flight_details = GetFlightOnDateDetailsResponse.model_construct(status='flying')
        api.get_flight_on_date_details.return_value = flight_details
        api.get_reservation_details.return_value = GetReservationDetailsResponse.model_construct(
            created_at=(datetime.now() - timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S"),
            cabin="basic_economy", 
            insurance="yes",
            flights=[Flight3.model_construct(
                flight_number='LY232',
                date="2025-02-28")],
        )

        guard_cancel_reservation(args, history, api)


if __name__ == '__main__':
    unittest.main()
