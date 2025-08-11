from unittest.mock import MagicMock, patch
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.update_reservation_baggages.guard_only_adding_checked_bags_is_allowed import guard_only_adding_checked_bags_is_allowed
from airline.i_airline import *
from datetime import datetime, timedelta

class TestGuardOnlyAddingCheckedBagsIsAllowed:
    
    def test_increase_checked_bags(self):
        """
        Policy: "You can update the baggage information of an existing reservation, allowing users to add additional checked bags."
        Example: "A reservation for ID 'AX37VB' initially has 2 checked bags, the airline agent calls UpdateReservationBaggages to increase the total checked bags to 3."
        """
        
        # mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True

        # mock other tools function return values
        reservation = Reservation(reservation_id="AX37VB", user_id="user123", origin="SFO", destination="JFK", flight_type="round_trip", cabin="economy", flights=[], passengers=[], payment_history=[], created_at="2023-01-01T00:00:00", total_baggages=2, nonfree_baggages=1, insurance="no", status=None)
        user = User(user_id="user123", name=Name(first_name="John", last_name="Doe"), address=Address(address1="123 Main St", address2=None, city="San Francisco", country="USA", state="CA", zip="94105"), email="john.doe@example.com", dob="1990-01-01", payment_methods={}, saved_passengers=[], membership="regular", reservations=[])

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "AX37VB" else None
        api.get_user_details.side_effect = lambda user_id: user if user_id == "user123" else None

        # invoke function under test
        guard_only_adding_checked_bags_is_allowed(history, api, reservation_id="AX37VB", total_baggages=3, nonfree_baggages=1, payment_id="credit_card_123")

    def test_add_checked_bags_from_zero(self):
        """
        Policy: "You can update the baggage information of an existing reservation, allowing users to add additional checked bags."
        Example: "For reservation ID 'ZL58NM', the agent prepares to add two more checked bag, increase 'total_baggages' from 0 to 2."
        """
        
        # mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True

        # mock other tools function return values
        reservation = Reservation(reservation_id="ZL58NM", user_id="user456", origin="LAX", destination="ORD", flight_type="one_way", cabin="business", flights=[], passengers=[], payment_history=[], created_at="2023-01-01T00:00:00", total_baggages=0, nonfree_baggages=0, insurance="no", status=None)
        user = User(user_id="user456", name=Name(first_name="Jane", last_name="Smith"), address=Address(address1="456 Elm St", address2=None, city="Los Angeles", country="USA", state="CA", zip="90001"), email="jane.smith@example.com", dob="1985-05-05", payment_methods={}, saved_passengers=[], membership="gold", reservations=[])

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZL58NM" else None
        api.get_user_details.side_effect = lambda user_id: user if user_id == "user456" else None

        # invoke function under test
        guard_only_adding_checked_bags_is_allowed(history, api, reservation_id="ZL58NM", total_baggages=2, nonfree_baggages=0, payment_id="gift_card_456")

    def test_reduce_checked_bags(self):
        """
        Policy: "Removing checked bags from the reservation is not permitted."
        Example: "Updating a reservation to reduce the total number of baggage items from 3 to 2 for reservation ID 'ZFA04Y'."
        """
        
        # mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True

        # mock other tools function return values
        reservation = Reservation(reservation_id="ZFA04Y", user_id="user789", origin="MIA", destination="ATL", flight_type="round_trip", cabin="economy", flights=[], passengers=[], payment_history=[], created_at="2023-01-01T00:00:00", total_baggages=3, nonfree_baggages=1, insurance="yes", status=None)
        user = User(user_id="user789", name=Name(first_name="Alice", last_name="Johnson"), address=Address(address1="789 Pine St", address2=None, city="Miami", country="USA", state="FL", zip="33101"), email="alice.johnson@example.com", dob="1980-10-10", payment_methods={}, saved_passengers=[], membership="silver", reservations=[])

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None
        api.get_user_details.side_effect = lambda user_id: user if user_id == "user789" else None

        # invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_only_adding_checked_bags_is_allowed(history, api, reservation_id="ZFA04Y", total_baggages=2, nonfree_baggages=1, payment_id="certificate_789")

    def test_reduce_checked_bags_to_one(self):
        """
        Policy: "Removing checked bags from the reservation is not permitted."
        Example: "updating a reservation 'total_baggages' to 1, previously it was set to 2 for reservation ID '5RN9XZ'."
        """
        
        # mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True

        # mock other tools function return values
        reservation = Reservation(reservation_id="5RN9XZ", user_id="user321", origin="SEA", destination="DEN", flight_type="one_way", cabin="basic_economy", flights=[], passengers=[], payment_history=[], created_at="2023-01-01T00:00:00", total_baggages=2, nonfree_baggages=1, insurance="no", status=None)
        user = User(user_id="user321", name=Name(first_name="Bob", last_name="Brown"), address=Address(address1="321 Oak St", address2=None, city="Seattle", country="USA", state="WA", zip="98101"), email="bob.brown@example.com", dob="1995-12-12", payment_methods={}, saved_passengers=[], membership="regular", reservations=[])

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "5RN9XZ" else None
        api.get_user_details.side_effect = lambda user_id: user if user_id == "user321" else None

        # invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_only_adding_checked_bags_is_allowed(history, api, reservation_id="5RN9XZ", total_baggages=1, nonfree_baggages=1, payment_id="credit_card_321")

    def test_remove_checked_bag(self):
        """
        Policy: "Removing checked bags from the reservation is not permitted."
        Example: "Despite the user requesting to remove a checked bag, the agent submits a request using UpdateReservationBaggages to change 'total_baggages' from 4 to 3."
        """
        
        # mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True

        # mock other tools function return values
        reservation = Reservation(reservation_id="XJ92KL", user_id="user654", origin="BOS", destination="PHX", flight_type="round_trip", cabin="business", flights=[], passengers=[], payment_history=[], created_at="2023-01-01T00:00:00", total_baggages=4, nonfree_baggages=2, insurance="yes", status=None)
        user = User(user_id="user654", name=Name(first_name="Charlie", last_name="Davis"), address=Address(address1="654 Maple St", address2=None, city="Boston", country="USA", state="MA", zip="02101"), email="charlie.davis@example.com", dob="1988-08-08", payment_methods={}, saved_passengers=[], membership="gold", reservations=[])

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "XJ92KL" else None
        api.get_user_details.side_effect = lambda user_id: user if user_id == "user654" else None

        # invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_only_adding_checked_bags_is_allowed(history, api, reservation_id="XJ92KL", total_baggages=3, nonfree_baggages=2, payment_id="gift_card_654")

    def test_remove_all_checked_bags(self):
        """
        Policy: "Removing checked bags from the reservation is not permitted."
        Example: "An agent mistakenly uses UpdateReservationBaggages and tries to adjust the total baggage count from 2 to 0 for reservation ID 'XJ92KL'."
        """
        
        # mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True

        # mock other tools function return values
        reservation = Reservation(reservation_id="XJ92KL", user_id="user654", origin="BOS", destination="PHX", flight_type="round_trip", cabin="business", flights=[], passengers=[], payment_history=[], created_at="2023-01-01T00:00:00", total_baggages=2, nonfree_baggages=1, insurance="yes", status=None)
        user = User(user_id="user654", name=Name(first_name="Charlie", last_name="Davis"), address=Address(address1="654 Maple St", address2=None, city="Boston", country="USA", state="MA", zip="02101"), email="charlie.davis@example.com", dob="1988-08-08", payment_methods={}, saved_passengers=[], membership="gold", reservations=[])

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "XJ92KL" else None
        api.get_user_details.side_effect = lambda user_id: user if user_id == "user654" else None

        # invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_only_adding_checked_bags_is_allowed(history, api, reservation_id="XJ92KL", total_baggages=0, nonfree_baggages=1, payment_id="certificate_654")
