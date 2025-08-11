from unittest.mock import MagicMock, patch
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.update_reservation_passengers.guard_updating_passengers_information import guard_updating_passengers_information
from airline.i_airline import *
from airline.airline_types import *
from datetime import datetime, timedelta

class TestGuardUpdatingPassengersInformation:

    def test_compliance_replace_passenger_with_details(self):
        """
        Policy: "Ensure all passengers including first name, last name, and date of birth."
        Example: "A user asks for replacing one passengers with another, providing all required details."
        """
        
        # mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True

        # mock other tools function return values 
        user = User(user_id="sara_doe_496", name=Name(first_name="Sara", last_name="Doe"), dob="1990-04-05", email="sara@example.com", address=Address(address1="123 Main St", address2=None, city="San Francisco", country="USA", state="CA", zip="94105"), payment_methods={}, saved_passengers=[], membership="gold", reservations=["ZFA04Y"])
        reservation = Reservation(reservation_id="ZFA04Y", user_id="sara_doe_496", origin="SFO", destination="JFK", flight_type="round_trip", cabin="business", flights=[], passengers=[Passenger(first_name="John", last_name="Doe", dob="1985-05-15")], payment_history=[], created_at=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"), total_baggages=2, nonfree_baggages=1, insurance="yes", status=None)

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "sara_doe_496" else None
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None
        
        #invoke function under test.
        guard_updating_passengers_information(history, api, reservation_id="ZFA04Y", passengers=[Passenger(first_name="Jane", last_name="Smith", dob="1992-07-20")])

    def test_violation_missing_date_of_birth(self):
        """
        Policy: "Ensure all passengers including first name, last name, and date of birth."
        Example: "An agent attempts updating passengers while missing the date of birth for each passenger."
        """
        
        # mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True

        # mock other tools function return values 
        user = User(user_id="sara_doe_496", name=Name(first_name="Sara", last_name="Doe"), dob="1990-04-05", email="sara@example.com", address=Address(address1="123 Main St", address2=None, city="San Francisco", country="USA", state="CA", zip="94105"), payment_methods={}, saved_passengers=[], membership="gold", reservations=["ZFA04Y"])
        reservation = Reservation(reservation_id="ZFA04Y", user_id="sara_doe_496", origin="SFO", destination="JFK", flight_type="round_trip", cabin="business", flights=[], passengers=[Passenger(first_name="John", last_name="Doe", dob="1985-05-15")], payment_history=[], created_at=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"), total_baggages=2, nonfree_baggages=1, insurance="yes", status=None)

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "sara_doe_496" else None
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None
        
        #invoke function under test.
        with pytest.raises(PolicyViolationException):
            guard_updating_passengers_information(history, api, reservation_id="ZFA04Y", passengers=[Passenger(first_name="Jane", last_name="Smith", dob="")])

    def test_violation_missing_first_name(self):
        """
        Policy: "Ensure all passengers including first name, last name, and date of birth."
        Example: "An agent attempts updating passengers information while missing a passenger's first name."
        """
        
        # mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True

        # mock other tools function return values 
        user = User(user_id="sara_doe_496", name=Name(first_name="Sara", last_name="Doe"), dob="1990-04-05", email="sara@example.com", address=Address(address1="123 Main St", address2=None, city="San Francisco", country="USA", state="CA", zip="94105"), payment_methods={}, saved_passengers=[], membership="gold", reservations=["ZFA04Y"])
        reservation = Reservation(reservation_id="ZFA04Y", user_id="sara_doe_496", origin="SFO", destination="JFK", flight_type="round_trip", cabin="business", flights=[], passengers=[Passenger(first_name="John", last_name="Doe", dob="1985-05-15")], payment_history=[], created_at=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"), total_baggages=2, nonfree_baggages=1, insurance="yes", status=None)

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "sara_doe_496" else None
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None
        
        #invoke function under test.
        with pytest.raises(PolicyViolationException):
            guard_updating_passengers_information(history, api, reservation_id="ZFA04Y", passengers=[Passenger(first_name="", last_name="Smith", dob="1992-07-20")])

    def test_violation_missing_last_name(self):
        """
        Policy: "Ensure all passengers including first name, last name, and date of birth."
        Example: "An agent attempts updating passengers information while missing a passenger's last name."
        """
        
        # mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True

        # mock other tools function return values 
        user = User(user_id="sara_doe_496", name=Name(first_name="Sara", last_name="Doe"), dob="1990-04-05", email="sara@example.com", address=Address(address1="123 Main St", address2=None, city="San Francisco", country="USA", state="CA", zip="94105"), payment_methods={}, saved_passengers=[], membership="gold", reservations=["ZFA04Y"])
        reservation = Reservation(reservation_id="ZFA04Y", user_id="sara_doe_496", origin="SFO", destination="JFK", flight_type="round_trip", cabin="business", flights=[], passengers=[Passenger(first_name="John", last_name="Doe", dob="1985-05-15")], payment_history=[], created_at=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"), total_baggages=2, nonfree_baggages=1, insurance="yes", status=None)

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "sara_doe_496" else None
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None
        
        #invoke function under test.
        with pytest.raises(PolicyViolationException):
            guard_updating_passengers_information(history, api, reservation_id="ZFA04Y", passengers=[Passenger(first_name="Jane", last_name="", dob="1992-07-20")])
