from unittest.mock import MagicMock, patch
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.book_reservation.guard_prohibition_on_modifying_user_s_passenger_count import guard_prohibition_on_modifying_user_s_passenger_count
from airline.airline_types import *
from airline.i_airline import *
from datetime import datetime, timedelta

class TestProhibitionOnModifyingPassengerCount:
    def setup_method(self):
        # Mock chat history
        self.history = MagicMock()
        self.history.ask_bool.return_value = True
        self.history.did_tool_return_value.return_value = True
        self.history.was_tool_called.return_value = True
        # Mock API
        self.api = MagicMock(spec=I_Airline)
        # Mock get_reservation_details to return a reservation with 2 passengers
        self.reservation = Reservation(
            reservation_id="RES123",
            user_id="sara_doe_496",
            origin="SFO",
            destination="JFK",
            flight_type="round_trip",
            cabin="economy",
            flights=[ReservationFlight(flight_number="HAT001", origin="SFO", destination="JFK", date="2024-05-01", price=500)],
            passengers=[
                Passenger(first_name="Sara", last_name="Doe", dob="1990-04-05"),
                Passenger(first_name="John", last_name="Smith", dob="1985-09-12")
            ],
            payment_history=[Payment(payment_id="PAY123", amount=1000)],
            created_at=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        self.api.get_reservation_details.side_effect = lambda reservation_id: self.reservation if reservation_id == "RES123" else None

    def test_update_passenger_details_without_changing_count(self):
        """
        Policy: "The agent must not alter the number of passengers in a reservation once established, though modifications to passenger details like name or date of birth are allowed."
        Example: "An agent updates passengers' details such as name spelling, date of birth, or contact information without changing the established number of passengers in the reservation."
        """
        passengers = [
            Passenger(first_name="Sara", last_name="Doe", dob="1990-04-05"),
            Passenger(first_name="John", last_name="Smith", dob="1985-09-13")  # Changed DOB
        ]
        # Should NOT raise PolicyViolationException
        try:
            guard_prohibition_on_modifying_user_s_passenger_count(
                self.history,
                self.api,
                user_id="sara_doe_496",
                origin="SFO",
                destination="JFK",
                flight_type="round_trip",
                cabin="economy",
                flights=[FlightInfo(flight_number="HAT001", date="2024-05-01")],
                passengers=passengers,
                payment_methods=[Payment(payment_id="PAY123", amount=1000)],
                total_baggages=2,
                nonfree_baggages=1,
                insurance="yes"
            )
        except PolicyViolationException as e:
            pytest.fail(f"Should not raise PolicyViolationException when only passenger details are updated. Error: {e}")

    def test_update_passenger_preferences_without_changing_count(self):
        """
        Policy: "The agent must not alter the number of passengers in a reservation once established, though modifications to passenger details like name or date of birth are allowed."
        Example: "Agent makes changes to existing passenger preferences like seat, dietary needs, or passport details while keeping the passenger count unchanged, demonstrating compliance with the policy."
        """
        passengers = [
            Passenger(first_name="Sara", last_name="Doe", dob="1990-04-05"),
            Passenger(first_name="John", last_name="Smith", dob="1985-09-12")
        ]
        # Should NOT raise PolicyViolationException
        try:
            guard_prohibition_on_modifying_user_s_passenger_count(
                self.history,
                self.api,
                user_id="sara_doe_496",
                origin="SFO",
                destination="JFK",
                flight_type="round_trip",
                cabin="economy",
                flights=[FlightInfo(flight_number="HAT001", date="2024-05-01")],
                passengers=passengers,
                payment_methods=[Payment(payment_id="PAY123", amount=1000)],
                total_baggages=2,
                nonfree_baggages=1,
                insurance="yes"
            )
        except PolicyViolationException as e:
            pytest.fail(f"Should not raise PolicyViolationException when only passenger preferences are updated. Error: {e}")

    def test_modify_passenger_count_increases(self):
        """
        Policy: "The agent must not alter the number of passengers in a reservation once established, though modifications to passenger details like name or date of birth are allowed."
        Example: "An agent attempts to alter the number of passengers in a reservation by changing the count, such as from 2 to 3, violating the policy of immutability on passenger count."
        """
        passengers = [
            Passenger(first_name="Sara", last_name="Doe", dob="1990-04-05"),
            Passenger(first_name="John", last_name="Smith", dob="1985-09-12"),
            Passenger(first_name="Alice", last_name="Brown", dob="1992-07-21")
        ]
        with pytest.raises(PolicyViolationException):
            guard_prohibition_on_modifying_user_s_passenger_count(
                self.history,
                self.api,
                user_id="sara_doe_496",
                origin="SFO",
                destination="JFK",
                flight_type="round_trip",
                cabin="economy",
                flights=[FlightInfo(flight_number="HAT001", date="2024-05-01")],
                passengers=passengers,
                payment_methods=[Payment(payment_id="PAY123", amount=1000)],
                total_baggages=2,
                nonfree_baggages=1,
                insurance="yes"
            )

    def test_modify_passenger_count_decreases(self):
        """
        Policy: "The agent must not alter the number of passengers in a reservation once established, though modifications to passenger details like name or date of birth are allowed."
        Example: "The reservation system allows an agent to add or remove passengers, such as reducing the passenger count established from 5 to 4, thereby violating the no-alteration policy."
        """
        passengers = [
            Passenger(first_name="Sara", last_name="Doe", dob="1990-04-05")
        ]
        with pytest.raises(PolicyViolationException):
            guard_prohibition_on_modifying_user_s_passenger_count(
                self.history,
                self.api,
                user_id="sara_doe_496",
                origin="SFO",
                destination="JFK",
                flight_type="round_trip",
                cabin="economy",
                flights=[FlightInfo(flight_number="HAT001", date="2024-05-01")],
                passengers=passengers,
                payment_methods=[Payment(payment_id="PAY123", amount=1000)],
                total_baggages=2,
                nonfree_baggages=1,
                insurance="yes"
            )

    def test_modify_passenger_count_without_user_consent(self):
        """
        Policy: "The agent must not alter the number of passengers in a reservation once established, though modifications to passenger details like name or date of birth are allowed."
        Example: "Without user consent, the agent modifies the passenger count from the initially scheduled 3 passengers to 2, which goes against the policy of maintaining a fixed passenger count."
        """
        # Simulate reservation with 3 passengers
        self.reservation.passengers = [
            Passenger(first_name="Sara", last_name="Doe", dob="1990-04-05"),
            Passenger(first_name="John", last_name="Smith", dob="1985-09-12"),
            Passenger(first_name="Alice", last_name="Brown", dob="1992-07-21")
        ]
        passengers = [
            Passenger(first_name="Sara", last_name="Doe", dob="1990-04-05"),
            Passenger(first_name="John", last_name="Smith", dob="1985-09-12")
        ]
        with pytest.raises(PolicyViolationException):
            guard_prohibition_on_modifying_user_s_passenger_count(
                self.history,
                self.api,
                user_id="sara_doe_496",
                origin="SFO",
                destination="JFK",
                flight_type="round_trip",
                cabin="economy",
                flights=[FlightInfo(flight_number="HAT001", date="2024-05-01")],
                passengers=passengers,
                payment_methods=[Payment(payment_id="PAY123", amount=1000)],
                total_baggages=2,
                nonfree_baggages=1,
                insurance="yes"
            )
