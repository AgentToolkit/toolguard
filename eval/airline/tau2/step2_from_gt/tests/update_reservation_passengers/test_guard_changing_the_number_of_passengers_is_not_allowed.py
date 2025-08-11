from unittest.mock import MagicMock, patch
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.update_reservation_passengers.guard_changing_the_number_of_passengers_is_not_allowed import guard_changing_the_number_of_passengers_is_not_allowed
from airline.i_airline import *
from airline.airline_types import *
from datetime import datetime, timedelta

class TestGuardChangingNumberOfPassengers:

    def test_correct_spelling_of_passenger_name(self):
        """
        Policy: "Users are restricted to only updating passenger details such as names or dates of birth within existing reservations."
        Example: "A user requests to correct the spelling of a passenger's name on their reservation."
        """
        
        # mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True

        # mock other tools function return values 
        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="user123",
            origin="SFO",
            destination="JFK",
            flight_type="round_trip",
            cabin="economy",
            flights=[],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[],
            created_at="2023-01-01T10:00:00",
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None
        
        # invoke function under test.
        guard_changing_the_number_of_passengers_is_not_allowed(history, api, reservation_id="ZFA04Y", passengers=[Passenger(first_name="Jon", last_name="Doe", dob="1990-01-01")])

    def test_add_additional_passenger(self):
        """
        Policy: "Users are not allowed to alter the total number of passengers included in a booking."
        Example: "A user attempts to update their reservation by adding an additional passenger."
        """
        
        # mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True

        # mock other tools function return values 
        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="user123",
            origin="SFO",
            destination="JFK",
            flight_type="round_trip",
            cabin="economy",
            flights=[],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[],
            created_at="2023-01-01T10:00:00",
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None
        
        # invoke function under test.
        with pytest.raises(PolicyViolationException):
            guard_changing_the_number_of_passengers_is_not_allowed(history, api, reservation_id="ZFA04Y", passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01"), Passenger(first_name="Jane", last_name="Doe", dob="1992-02-02")])

    def test_remove_existing_passenger(self):
        """
        Policy: "Users are not allowed to alter the total number of passengers included in a booking."
        Example: "A user requests the agent to remove an existing passenger from their reservation."
        """
        
        # mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True

        # mock other tools function return values 
        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="user123",
            origin="SFO",
            destination="JFK",
            flight_type="round_trip",
            cabin="economy",
            flights=[],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01"), Passenger(first_name="Jane", last_name="Doe", dob="1992-02-02")],
            payment_history=[],
            created_at="2023-01-01T10:00:00",
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None
        
        # invoke function under test.
        with pytest.raises(PolicyViolationException):
            guard_changing_the_number_of_passengers_is_not_allowed(history, api, reservation_id="ZFA04Y", passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")])
