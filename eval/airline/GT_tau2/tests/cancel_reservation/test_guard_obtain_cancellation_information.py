from unittest.mock import MagicMock, patch
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.cancel_reservation.guard_obtain_cancellation_information import guard_obtain_cancellation_information
from airline.i_airline import *

class TestGuardObtainCancellationInformation:

    def test_successfully_canceling_reservation_with_all_info(self):
        # Policy: "Before invoking the 'cancel_reservation' tool, ensure you have gathered the user's ID, reservation ID, and cancellation reason."
        # Example: "Successfully canceling reservation '4WQ150' with the user's ID 'chen_jackson_3290' and the reason for cancellation as 'change of plans'."
        
        # Mock the history service:
        history = MagicMock()
        history.ask.return_value = 'change of plans'

        # Mock other tools function return values
        user = User.model_construct(user_id='chen_jackson_3290', name=Name(first_name='Chen', last_name='Jackson'), address=Address(address1='123 Main St', address2=None, city='Anytown', country='USA', state='CA', zip='12345'), email='chen.jackson@example.com', dob='1990-01-01', payment_methods={}, saved_passengers=[], membership='regular', reservations=['4WQ150'])
        reservation = Reservation.model_construct(reservation_id='4WQ150', user_id='chen_jackson_3290', origin='JFK', destination='LAX', flight_type='round_trip', cabin='economy', flights=[], passengers=[], payment_history=[], created_at='2023-10-01T10:00:00', total_baggages=2, nonfree_baggages=1, insurance='yes')

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == 'chen_jackson_3290' else None
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == '4WQ150' else None
        
        # Invoke function under test.
        guard_obtain_cancellation_information(history, api, '4WQ150')

    def test_attempting_to_cancel_reservation_without_user_id_and_reason(self):
        # Policy: "Before invoking the 'cancel_reservation' tool, ensure you have gathered the user's ID, reservation ID, and cancellation reason."
        # Example: "Attempting to cancel a reservation where the reservation ID '4WQ150' is provided, but the user ID and cancellation reason are missing."
        
        # Mock the history service:
        history = MagicMock()
        history.ask.return_value = None

        # Mock other tools function return values
        reservation = Reservation.model_construct(reservation_id='4WQ150', user_id='chen_jackson_3290', origin='JFK', destination='LAX', flight_type='round_trip', cabin='economy', flights=[], passengers=[], payment_history=[], created_at='2023-10-01T10:00:00', total_baggages=2, nonfree_baggages=1, insurance='yes')

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: None
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == '4WQ150' else None
        
        # Invoke function under test.
        with pytest.raises(PolicyViolationException):
            guard_obtain_cancellation_information(history, api, '4WQ150')

    def test_cancel_reservation_without_reason_for_cancellation(self):
        # Policy: "Before invoking the 'cancel_reservation' tool, ensure you have gathered the user's ID, reservation ID, and cancellation reason."
        # Example: "A request to invoke 'cancel_reservation' with reservation ID 'ZFA04Y' without specifying the user's ID or the reason for cancellation."
        
        # Mock the history service:
        history = MagicMock()
        history.ask.return_value = None

        # Mock other tools function return values
        user = User.model_construct(user_id='diana_smith_5689', name=Name(first_name='Diana', last_name='Smith'), address=Address(address1='456 Elm St', address2=None, city='Othertown', country='USA', state='NY', zip='67890'), email='diana.smith@example.com', dob='1985-05-05', payment_methods={}, saved_passengers=[], membership='gold', reservations=['ZFA04Y'])
        reservation = Reservation.model_construct(reservation_id='ZFA04Y', user_id='diana_smith_5689', origin='LAX', destination='JFK', flight_type='one_way', cabin='business', flights=[], passengers=[], payment_history=[], created_at='2023-10-01T10:00:00', total_baggages=1, nonfree_baggages=0, insurance='no')

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == 'diana_smith_5689' else None
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == 'ZFA04Y' else None
        
        # Invoke function under test.
        with pytest.raises(PolicyViolationException):
            guard_obtain_cancellation_information(history, api, 'ZFA04Y')
