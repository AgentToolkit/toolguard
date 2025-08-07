from unittest.mock import MagicMock, patch
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.book_reservation.guard_checked_bag_allowance_by_membership_tier import guard_checked_bag_allowance_by_membership_tier
from airline.i_airline import I_Airline
from airline.airline_types import *
from datetime import datetime, timedelta

class TestGuardCheckedBagAllowanceByMembershipTier:

    def test_regular_member_business_class_two_free_bags(self):
        """
        Policy: "Regular members have 2 free checked bags for business class."
        Example: "A regular member books a business class flight with 2 free checked bags for a single passenger."
        """
        history = MagicMock()
        history.ask_bool.return_value = True

        user = User(user_id="user123", name=Name(first_name="John", last_name="Doe"), address=Address(address1="123 Main St", address2="", city="Anytown", country="USA", state="CA", zip="12345"), email="john.doe@example.com", dob="1990-01-01", payment_methods={}, saved_passengers=[], membership="regular", reservations=[])

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "user123" else None

        flights = [FlightInfo(flight_number="FL123", date="2024-05-01")]
        passengers = [Passenger(first_name="John", last_name="Doe", dob="1990-01-01")]
        payment_methods = [Payment(payment_id="pay123", amount=0)]

        guard_checked_bag_allowance_by_membership_tier(
            history=history,
            api=api,
            user_id="user123",
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin="business",
            flights=flights,
            passengers=passengers,
            payment_methods=payment_methods,
            total_baggages=2,
            nonfree_baggages=0,
            insurance="no"
        )

    def test_regular_member_basic_economy_one_free_bag_violation(self):
        """
        Policy: "Regular members have 0 free checked bags for basic economy."
        Example: "A regular member books a flight in basic economy class with 1 free checked bag."
        """
        history = MagicMock()
        history.ask_bool.return_value = True

        user = User(user_id="user123", name=Name(first_name="John", last_name="Doe"), address=Address(address1="123 Main St", address2="", city="Anytown", country="USA", state="CA", zip="12345"), email="john.doe@example.com", dob="1990-01-01", payment_methods={}, saved_passengers=[], membership="regular", reservations=[])

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "user123" else None

        flights = [FlightInfo(flight_number="FL123", date="2024-05-01")]
        passengers = [Passenger(first_name="John", last_name="Doe", dob="1990-01-01")]
        payment_methods = [Payment(payment_id="pay123", amount=0)]

        with pytest.raises(PolicyViolationException):
            guard_checked_bag_allowance_by_membership_tier(
                history=history,
                api=api,
                user_id="user123",
                origin="SFO",
                destination="JFK",
                flight_type="one_way",
                cabin="basic_economy",
                flights=flights,
                passengers=passengers,
                payment_methods=payment_methods,
                total_baggages=1,
                nonfree_baggages=0,
                insurance="no"
            )

    def test_gold_member_economy_four_checked_bags(self):
        """
        Policy: "Gold members have 3 free checked bags for economy class."
        Example: "A gold member books an economy class flight with 4 checked bags, where he pays for one and the other three are free."
        """
        history = MagicMock()
        history.ask_bool.return_value = True

        user = User(user_id="user456", name=Name(first_name="Jane", last_name="Smith"), address=Address(address1="456 Elm St", address2="", city="Othertown", country="USA", state="NY", zip="67890"), email="jane.smith@example.com", dob="1985-05-05", payment_methods={}, saved_passengers=[], membership="gold", reservations=[])

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "user456" else None

        flights = [FlightInfo(flight_number="FL456", date="2024-06-01")]
        passengers = [Passenger(first_name="Jane", last_name="Smith", dob="1985-05-05")]
        payment_methods = [Payment(payment_id="pay456", amount=50)]

        guard_checked_bag_allowance_by_membership_tier(
            history=history,
            api=api,
            user_id="user456",
            origin="LAX",
            destination="ORD",
            flight_type="round_trip",
            cabin="economy",
            flights=flights,
            passengers=passengers,
            payment_methods=payment_methods,
            total_baggages=4,
            nonfree_baggages=1,
            insurance="yes"
        )

    def test_silver_member_basic_economy_two_bags_violation(self):
        """
        Policy: "Silver members have 1 free checked bag for basic economy."
        Example: "A silver member with one bag books a basic economy class flight and is charged for his single bag."
        """
        history = MagicMock()
        history.ask_bool.return_value = True

        user = User(user_id="user789", name=Name(first_name="Alice", last_name="Johnson"), address=Address(address1="789 Pine St", address2="", city="Sometown", country="USA", state="TX", zip="54321"), email="alice.johnson@example.com", dob="1975-07-07", payment_methods={}, saved_passengers=[], membership="silver", reservations=[])

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "user789" else None

        flights = [FlightInfo(flight_number="FL789", date="2024-07-01")]
        passengers = [Passenger(first_name="Alice", last_name="Johnson", dob="1975-07-07")]
        payment_methods = [Payment(payment_id="pay789", amount=0)]

        with pytest.raises(PolicyViolationException):
            guard_checked_bag_allowance_by_membership_tier(
                history=history,
                api=api,
                user_id="user789",
                origin="MIA",
                destination="ATL",
                flight_type="one_way",
                cabin="basic_economy",
                flights=flights,
                passengers=passengers,
                payment_methods=payment_methods,
                total_baggages=1,
                nonfree_baggages=0,
                insurance="no"
            )

    def test_gold_member_basic_economy_three_free_bags_violation(self):
        """
        Policy: "Gold members have 2 free checked bags for basic economy."
        Example: "A gold member reserves a basic economy ticket and receives 3 free checked bags."
        """
        history = MagicMock()
        history.ask_bool.return_value = True

        user = User(user_id="user101", name=Name(first_name="Bob", last_name="Brown"), address=Address(address1="101 Maple St", address2="", city="Newcity", country="USA", state="FL", zip="98765"), email="bob.brown@example.com", dob="1980-08-08", payment_methods={}, saved_passengers=[], membership="gold", reservations=[])

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda user_id: user if user_id == "user101" else None

        flights = [FlightInfo(flight_number="FL101", date="2024-08-01")]
        passengers = [Passenger(first_name="Bob", last_name="Brown", dob="1980-08-08")]
        payment_methods = [Payment(payment_id="pay101", amount=0)]

        with pytest.raises(PolicyViolationException):
            guard_checked_bag_allowance_by_membership_tier(
                history=history,
                api=api,
                user_id="user101",
                origin="SEA",
                destination="DEN",
                flight_type="round_trip",
                cabin="basic_economy",
                flights=flights,
                passengers=passengers,
                payment_methods=payment_methods,
                total_baggages=3,
                nonfree_baggages=0,
                insurance="yes"
            )
