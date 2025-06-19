import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

# Importing necessary modules
from my_app.cancel_reservation.guard_cancel_reservation import guard_cancel_reservation
from my_app.common import *
from my_app.domain import *


class TestGuardCancellationConditions(unittest.TestCase):
    
    # Compliance Tests
    def test_cancel_within_24_hours_compliance(self):
        """
        Test c§ase: A user requests to cancel their reservation immediately, and the booking was made 12 hours ago, thus complying with the within-24-hours rule.
        """
        args = CancelReservationRequest.model_construct(reservation_id="ZFA04Y")
        history = MagicMock()
        history.ask_bool.return_value = True

        api = MagicMock()
        api.get_flight_on_date_details.return_value = GetFlightOnDateDetailsResponse.model_construct(status="available")
        api.get_reservation_details.return_value = GetReservationDetailsResponse.model_construct(
            flights=[Flight3.model_construct(
                flight_number='LY232',
                date="2025-02-28"
            )],
            created_at=(datetime.now() - timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S")
        )

        guard_cancel_reservation(args, history, api)

    def test_airline_canceled_flight_compliance(self):
        """
        Test case: The agent cancels a reservation after verifying that the airline has canceled the flight, thus ensuring compliance with policy conditions.
        """
        args = CancelReservationRequest.model_construct(reservation_id="ZFA04Y")
        history = MagicMock()
        history.ask_bool.return_value = True

        api = MagicMock()
        api.get_flight_on_date_details.return_value = GetFlightOnDateDetailsResponse.model_construct(status="cancelled")
        api.get_reservation_details.return_value = GetReservationDetailsResponse.model_construct(
            flights=[Flight3.model_construct(
                flight_number='LY232',
                date="2025-02-28"
            )],
            created_at=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
        )

        guard_cancel_reservation(args, history, api)

    def test_basic_economy_health_insurance_compliance(self):
        """
        Test case: A user books a Basic Economy flight, purchases travel insurance, and cancels due to a health issue, complying with the conditions required for such cancellations.
        """
        args = CancelReservationRequest.model_construct(reservation_id="ZFA04Y")
        history = MagicMock()
        history.ask_bool.return_value = True

        api = MagicMock()
        api.get_reservation_details.return_value = GetReservationDetailsResponse.model_construct(
            created_at=(datetime.now() - timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S"),
            cabin="basic_economy", 
            insurance="yes",
            flights=[Flight3.model_construct(
                flight_number='LY232',
                date="2025-02-28")],
        )

        guard_cancel_reservation(args, history, api)

    # Violation Tests
    def test_cancel_after_48_hours_violation(self):
        """
        Test case: A user requests to cancel a reservation made 48 hours ago without any special conditions met, like an airline cancellation or having travel insurance, which violates the policy's condition of a 24-hour cancellation window or required travel insurance.
        """
        args = CancelReservationRequest.model_construct(reservation_id="ZFA04Y")
        history = MagicMock()
        history.ask_bool.return_value = False

        api = MagicMock()
        reservation = GetReservationDetailsResponse.model_construct(
            flights=[Flight3.model_construct(flight_number='fl123', date='Apr 12 2025')],
            created_at=(datetime.now() - timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S")
        )
        api.get_reservation_details.return_value = reservation

        with self.assertRaises(PolicyViolationException):
            guard_cancel_reservation(args, history, api)

    def test_economy_no_insurance_violation(self):
        """
        Test case: An agent attempts to cancel an economy class reservation without verifying if the user had purchased travel insurance for health or weather-related cancellations, not adhering to the policy's stipulations for Economy bookings.
        """
        args = CancelReservationRequest.model_construct(reservation_id="ZFA04Y")
        history = MagicMock()
        history.ask_bool.return_value = False

        api = MagicMock()
        reservation = GetReservationDetailsResponse.model_construct(
            flights=[Flight3.model_construct(flight_number='fl123', date='Apr 12 2025')],
            created_at=(datetime.now() - timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S"),
            cabin="economy", 
            insurance="no"
        )
        api.get_reservation_details.return_value = reservation

        with self.assertRaises(PolicyViolationException):
            guard_cancel_reservation(args, history, api)

if __name__ == '__main__':
    unittest.main()
