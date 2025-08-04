from unittest.mock import MagicMock, patch
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.cancel_reservation.guard_cancellation_of_entire_trips_only import guard_cancellation_of_entire_trips_only
from airline.i_airline import *

class TestGuardCancellationOfEntireTripsOnly:

    def test_compliance_all_segments_scheduled(self):
        # Policy: "Before using the CancelReservation tool, the agent should confirm that the entire trip is unused."
        # Example: "An agent receives a user request for cancellation and checks each flight segment to ensure none have been flown or taken off."
        
        # Mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True  # Mock that True is the answer to the question

        # Mock other tools function return values
        reservation = Reservation.model_construct(
            reservation_id='ZFA04Y',
            user_id='user123',
            origin='JFK',
            destination='LAX',
            flight_type='round_trip',
            cabin='economy',
            flights=[
                ReservationFlight.model_construct(flight_number='FL123', date='2024-05-01', price=200),
                ReservationFlight.model_construct(flight_number='FL456', date='2024-05-02', price=200)
            ],
            passengers=[Passenger.model_construct(first_name='John', last_name='Doe', dob='1990-01-01')],
            payment_history=[],
            created_at='2023-11-01T10:00:00',
            total_baggages=2,
            nonfree_baggages=1,
            insurance='yes'
        )

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.return_value = reservation
        api.get_flight_status.side_effect = lambda flight_number, date: 'scheduled' if flight_number in ['FL123', 'FL456'] else 'unknown'

        # Invoke function under test.
        try:
            guard_cancellation_of_entire_trips_only(history, api, 'ZFA04Y')
        except PolicyViolationException:
            pytest.fail("PolicyViolationException was raised unexpectedly when all segments are scheduled.")

    def test_violation_segment_flying(self):
        # Policy: "Before using the CancelReservation tool, the agent should confirm that the entire trip is unused."
        # Example: "The agent receives a request to cancel a trip, and while one of the segments shows a 'flying' status, the agent proceeds with CancelReservation."
        
        # Mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True  # Mock that True is the answer to the question

        # Mock other tools function return values
        reservation = Reservation.model_construct(
            reservation_id='ZFA04Y',
            user_id='user123',
            origin='JFK',
            destination='LAX',
            flight_type='round_trip',
            cabin='economy',
            flights=[
                ReservationFlight.model_construct(flight_number='FL123', date='2024-05-01', price=200),
                ReservationFlight.model_construct(flight_number='FL456', date='2024-05-02', price=200)
            ],
            passengers=[Passenger.model_construct(first_name='John', last_name='Doe', dob='1990-01-01')],
            payment_history=[],
            created_at='2023-11-01T10:00:00',
            total_baggages=2,
            nonfree_baggages=1,
            insurance='yes'
        )

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.return_value = reservation
        api.get_flight_status.side_effect = lambda flight_number, date: 'flying' if flight_number == 'FL123' else 'scheduled'

        # Invoke function under test.
        with pytest.raises(PolicyViolationException):
            guard_cancellation_of_entire_trips_only(history, api, 'ZFA04Y')
