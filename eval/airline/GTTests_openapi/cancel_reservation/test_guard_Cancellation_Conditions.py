import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

# Importing necessary modules
from airline.cancel_reservation.guard_cancel_reservation import guard_cancel_reservation
from airline.common import *
from airline.domain import *

FLIGHTS = {
    'LANDED':{
        "2025-02-28": GetFlightInstanceResponse(status="landed")
    },
    'FLYING':{
        "2025-02-28": GetFlightInstanceResponse(status="flying")
    },
    'DELAYED':{
        "2025-02-28": GetFlightInstanceResponse(status="delayed")
    },
    'ON_TIME':{
        "2025-02-28": GetFlightInstanceResponse(status="on_time")
    },
    'AVAIL':{
        "2025-02-28": GetFlightInstanceResponse(status="available")
    },
    'CANCELLED':{
        "2025-02-28": GetFlightInstanceResponse(status="cancelled")
    },
    "ANOTHER ONE":{
        "2025-02-28": GetFlightInstanceResponse(status="available")
    }
}
class TestGuardCancellationConditions(unittest.TestCase):

    def story(self, flight_id:str, hours_ago:int):
        history = MagicMock()
        history.ask_bool.return_value = False

        api = MagicMock()

        def get_flight(q:GetFlightInstanceParametersQuery):
            return FLIGHTS.get(q.flight_id, {}).get(q.date)
        api.get_flight_instance.side_effect = get_flight

        reservation = GetReservationDetailsResponse(
            reservation_id="12ds",
            flights=[
                Flight3( flight_number=flight_id, date="2025-02-28"),
                Flight3( flight_number="ANOTHER ONE", date="2025-02-28"),
            ],
            passengers=[
                Passenger2(first_name="John", last_name="Doe", dob="1990-01-01")
            ],
            payment_history=[
                PaymentHistoryItem2(payment_id="asas", amount=39)
            ],
            created_at=(datetime.now() - timedelta(hours=hours_ago)).strftime("%Y-%m-%d %H:%M:%S"),
            cabin="basic_economy",
            origin="JFK",
            destination="SFO",
            user_id="qwq",
            flight_type="one-way",
            insurance="no",
        )
        def get_resrv(q:GetReservationDetailsParametersQuery):
            if q.reservation_id == reservation.reservation_id:
                return reservation
        api.get_reservation_details.side_effect = get_resrv

        return api, history, reservation

    # Violation test: Agent cancels without checking flight status
    def test_within_12h_but_landed(self):
        """
        Test case: An agent cancels a reservation without checking if any flight segment has been flown and finds out post-operation that one of the flights was already completed, violating policy requirements.
        """
        api, history, reserv = self.story('LANDED', 12)
        args = CancelReservationRequest(reservation_id=reserv.reservation_id)
        with self.assertRaises(PolicyViolationException):
            guard_cancel_reservation(args, history, api)

    def test_within_12h_but_is_flying(self):
        api, history, reserv = self.story("FLYING", 12)
        args = CancelReservationRequest(reservation_id=reserv.reservation_id)
        with self.assertRaises(PolicyViolationException):
            guard_cancel_reservation(args, history, api)
    
    # Compliance Tests
    def test_avail_within_12_hours_compliance(self):
        """
        Test case: A user requests to cancel their reservation immediately, and the booking was made 12 hours ago, thus complying with the within-24-hours rule.
        """
        api, history, reserv = self.story("AVAIL", 12)
        args = CancelReservationRequest(reservation_id=reserv.reservation_id)
        guard_cancel_reservation(args, history, api)

    def test_delayed_within_12_hours_compliance(self):
        """
        Test case: A user requests to cancel their reservation immediately, and the booking was made 12 hours ago, thus complying with the within-24-hours rule.
        """
        api, history, reserv = self.story("DELAYED", 12)
        args = CancelReservationRequest(reservation_id=reserv.reservation_id)
        guard_cancel_reservation(args, history, api)

    def test_ontime_within_12_hours_compliance(self):
        """
        Test case: A user requests to cancel their reservation immediately, and the booking was made 12 hours ago, thus complying with the within-24-hours rule.
        """
        api, history, reserv = self.story("ON_TIME", 12)
        args = CancelReservationRequest(reservation_id=reserv.reservation_id)
        guard_cancel_reservation(args, history, api)

    def test_airline_canceled_flight_compliance(self):
        """
        Test case: The agent cancels a reservation after verifying that the airline has canceled the flight, thus ensuring compliance with policy conditions.
        """
        api, history, reserv = self.story("CANCELLED", 24*365)
        args = CancelReservationRequest(reservation_id=reserv.reservation_id)
        guard_cancel_reservation(args, history, api)

    def test_has_insurance_health_reason_compliance(self):
        """
        Test case: A user books a Basic Economy flight, purchases travel insurance, and cancels due to a health issue, complying with the conditions required for such cancellations.
        """
        api, history, reserv = self.story("AVAIL", 24*2)
        reserv.cabin="basic_economy"
        reserv.insurance="yes"
        history.ask_bool.return_value = True
        args = CancelReservationRequest(reservation_id=reserv.reservation_id)
        guard_cancel_reservation(args, history, api)

    def test_has_insurance_other_reason_compliance(self):
        """
        Test case: A user books a Basic Economy flight, purchases travel insurance, and cancels due to a health issue, complying with the conditions required for such cancellations.
        """
        api, history, reserv = self.story("AVAIL", 24*2)
        reserv.cabin="basic_economy"
        reserv.insurance="yes"
        history.ask_bool.return_value = False
        args = CancelReservationRequest(reservation_id=reserv.reservation_id)
        with self.assertRaises(PolicyViolationException):
            guard_cancel_reservation(args, history, api)

    # Violation Tests
    def test_basic_economy_cannot_cancel_after_48_hours_violation(self):
        api, history, reserv = self.story("AVAIL", 24*2)
        reserv.cabin="basic_economy"
        reserv.insurance="no"
        args = CancelReservationRequest(reservation_id=reserv.reservation_id)

        with self.assertRaises(PolicyViolationException):
            guard_cancel_reservation(args, history, api)

    def test_economy_cannot_cancel_after_48_hours_violation(self):
        api, history, reserv = self.story("AVAIL", 24*2)
        reserv.cabin="economy"
        reserv.insurance="no"
        args = CancelReservationRequest(reservation_id=reserv.reservation_id)

        with self.assertRaises(PolicyViolationException):
            guard_cancel_reservation(args, history, api)

    def test_business_can_always_cancel(self):
        api, history, reserv = self.story("AVAIL", 24*10)
        reserv.cabin="business"
        reserv.insurance="no"
        args = CancelReservationRequest(reservation_id=reserv.reservation_id)

        guard_cancel_reservation(args, history, api)


if __name__ == '__main__':
    unittest.main()
