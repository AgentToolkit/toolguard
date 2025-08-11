from unittest.mock import MagicMock
import pytest
from datetime import datetime, timedelta
from rt_toolguard.data_types import PolicyViolationException, ChatHistory
from airline.update_reservation_passengers.guard_validate_passenger_number_consistency import guard_validate_passenger_number_consistency
from airline.airline_types import Passenger, Reservation
from airline.i_airline import I_Airline

class TestValidatePassengerNumberConsistency:
    def setup_method(self):
        # Mock chat history
        self.history = MagicMock(spec=ChatHistory)
        # Mock API
        self.api = MagicMock(spec=I_Airline)
        # Common reservation_id for all tests
        self.reservation_id = "ZFA04Y"
        # Mock get_reservation_details to return a reservation with a specific number of passengers
        self.api.get_reservation_details.side_effect = self._mock_get_reservation_details

    def _mock_get_reservation_details(self, reservation_id):
        # Return a reservation with the correct number of passengers for each test
        if reservation_id == "ZFA04Y":
            # Used in compliance and violation tests, will be overwritten in each test
            return self._reservation
        return None

    def test_update_name_and_dob_same_count(self):
        """
        Policy: "When modifying passenger details in a reservation using ToolX, ensure the number of passengers remains the same."
        Example: "A user updates the reservation 'ZFA04Y', originally for 3 passengers, by changing the name and date of birth of a passenger while maintaining the total number unchanged, adhering to the passenger number consistency policy."
        """
        # Setup original reservation with 3 passengers
        self._reservation = Reservation(
            reservation_id=self.reservation_id,
            user_id="user_123",
            origin="JFK",
            destination="LAX",
            flight_type="one_way",
            cabin="economy",
            flights=[],
            passengers=[
                Passenger(first_name="Alice", last_name="Smith", dob="1990-01-01"),
                Passenger(first_name="Bob", last_name="Jones", dob="1985-05-05"),
                Passenger(first_name="Carol", last_name="White", dob="1978-12-12")
            ],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="no",
            status=None
        )
        # Update passenger details, but keep count the same
        updated_passengers = [
            Passenger(first_name="Alice", last_name="Smith", dob="1990-01-01"),
            Passenger(first_name="Bob", last_name="Johnson", dob="1985-05-05"),  # last name changed
            Passenger(first_name="Carol", last_name="White", dob="1978-12-13")   # dob changed
        ]
        try:
            guard_validate_passenger_number_consistency(self.history, self.api, self.reservation_id, updated_passengers)
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: Expected no exception when updating passenger details without changing count. Got: {e.message}")

    def test_correct_spelling_names_same_count(self):
        """
        Policy: "When modifying passenger details in a reservation using ToolX, ensure the number of passengers remains the same."
        Example: "An update is requested for reservation 'ZFA04Y' to correct spelling errors in passengers' names, ensuring the list retains its original size of 2 passengers, thus complying with the policy."
        """
        self._reservation = Reservation(
            reservation_id=self.reservation_id,
            user_id="user_456",
            origin="SFO",
            destination="ORD",
            flight_type="round_trip",
            cabin="business",
            flights=[],
            passengers=[
                Passenger(first_name="Jon", last_name="Doe", dob="1992-03-03"),
                Passenger(first_name="Sara", last_name="Lee", dob="1991-07-07")
            ],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="yes",
            status=None
        )
        updated_passengers = [
            Passenger(first_name="John", last_name="Doe", dob="1992-03-03"),  # spelling corrected
            Passenger(first_name="Sarah", last_name="Lee", dob="1991-07-07")   # spelling corrected
        ]
        try:
            guard_validate_passenger_number_consistency(self.history, self.api, self.reservation_id, updated_passengers)
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: Expected no exception when correcting spelling with same passenger count. Got: {e.message}")

    def test_modify_ages_no_count_change(self):
        """
        Policy: "When modifying passenger details in a reservation using ToolX, ensure the number of passengers remains the same."
        Example: "User modifies passenger ages in the reservation with ID 'ZFA04Y', containing 4 passengers, ensuring no passenger is added or removed, thus correctly validating the number consistency as per the policy requirements."
        """
        self._reservation = Reservation(
            reservation_id=self.reservation_id,
            user_id="user_789",
            origin="ATL",
            destination="MIA",
            flight_type="one_way",
            cabin="basic_economy",
            flights=[],
            passengers=[
                Passenger(first_name="Tom", last_name="Brown", dob="2000-01-01"),
                Passenger(first_name="Jerry", last_name="Black", dob="2001-02-02"),
                Passenger(first_name="Spike", last_name="Green", dob="2002-03-03"),
                Passenger(first_name="Tyke", last_name="Blue", dob="2003-04-04")
            ],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=3,
            nonfree_baggages=2,
            insurance="no",
            status=None
        )
        updated_passengers = [
            Passenger(first_name="Tom", last_name="Brown", dob="2000-01-02"),  # dob changed
            Passenger(first_name="Jerry", last_name="Black", dob="2001-02-03"),
            Passenger(first_name="Spike", last_name="Green", dob="2002-03-04"),
            Passenger(first_name="Tyke", last_name="Blue", dob="2003-04-05")
        ]
        try:
            guard_validate_passenger_number_consistency(self.history, self.api, self.reservation_id, updated_passengers)
        except PolicyViolationException as e:
            pytest.fail(f"Test failed: Expected no exception when modifying ages with same passenger count. Got: {e.message}")

    def test_update_to_fewer_passengers_raises(self):
        """
        Policy: "When modifying passenger details in a reservation using ToolX, ensure the number of passengers remains the same."
        Example: "A user attempts to update a reservation with ID 'ZFA04Y', initially having 3 passengers, to an updated list containing only 2 passengers, violating the rule that the number of passengers must remain unchanged."
        """
        self._reservation = Reservation(
            reservation_id=self.reservation_id,
            user_id="user_123",
            origin="JFK",
            destination="LAX",
            flight_type="one_way",
            cabin="economy",
            flights=[],
            passengers=[
                Passenger(first_name="Alice", last_name="Smith", dob="1990-01-01"),
                Passenger(first_name="Bob", last_name="Jones", dob="1985-05-05"),
                Passenger(first_name="Carol", last_name="White", dob="1978-12-12")
            ],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="no",
            status=None
        )
        updated_passengers = [
            Passenger(first_name="Alice", last_name="Smith", dob="1990-01-01"),
            Passenger(first_name="Bob", last_name="Jones", dob="1985-05-05")
        ]
        with pytest.raises(PolicyViolationException):
            guard_validate_passenger_number_consistency(self.history, self.api, self.reservation_id, updated_passengers)

    def test_add_extra_passenger_raises(self):
        """
        Policy: "When modifying passenger details in a reservation using ToolX, ensure the number of passengers remains the same."
        Example: "A user tries to modify the reservation 'ZFA04Y' by adding a fourth passenger when the reservation originally included 3 passengers, which incorrectly alters the total count of passengers."
        """
        self._reservation = Reservation(
            reservation_id=self.reservation_id,
            user_id="user_123",
            origin="JFK",
            destination="LAX",
            flight_type="one_way",
            cabin="economy",
            flights=[],
            passengers=[
                Passenger(first_name="Alice", last_name="Smith", dob="1990-01-01"),
                Passenger(first_name="Bob", last_name="Jones", dob="1985-05-05"),
                Passenger(first_name="Carol", last_name="White", dob="1978-12-12")
            ],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="no",
            status=None
        )
        updated_passengers = [
            Passenger(first_name="Alice", last_name="Smith", dob="1990-01-01"),
            Passenger(first_name="Bob", last_name="Jones", dob="1985-05-05"),
            Passenger(first_name="Carol", last_name="White", dob="1978-12-12"),
            Passenger(first_name="Dave", last_name="Green", dob="1992-02-02")
        ]
        with pytest.raises(PolicyViolationException):
            guard_validate_passenger_number_consistency(self.history, self.api, self.reservation_id, updated_passengers)

    def test_update_to_five_passengers_raises(self):
        """
        Policy: "When modifying passenger details in a reservation using ToolX, ensure the number of passengers remains the same."
        Example: "User requests an update on reservation 'ZFA04Y' by submitting a list of 5 passengers, while the original reservation only contained 4, thus conflicting with the passenger count policy."
        """
        self._reservation = Reservation(
            reservation_id=self.reservation_id,
            user_id="user_789",
            origin="ATL",
            destination="MIA",
            flight_type="one_way",
            cabin="basic_economy",
            flights=[],
            passengers=[
                Passenger(first_name="Tom", last_name="Brown", dob="2000-01-01"),
                Passenger(first_name="Jerry", last_name="Black", dob="2001-02-02"),
                Passenger(first_name="Spike", last_name="Green", dob="2002-03-03"),
                Passenger(first_name="Tyke", last_name="Blue", dob="2003-04-04")
            ],
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=3,
            nonfree_baggages=2,
            insurance="no",
            status=None
        )
        updated_passengers = [
            Passenger(first_name="Tom", last_name="Brown", dob="2000-01-01"),
            Passenger(first_name="Jerry", last_name="Black", dob="2001-02-02"),
            Passenger(first_name="Spike", last_name="Green", dob="2002-03-03"),
            Passenger(first_name="Tyke", last_name="Blue", dob="2003-04-04"),
            Passenger(first_name="New", last_name="Person", dob="2004-05-05")
        ]
        with pytest.raises(PolicyViolationException):
            guard_validate_passenger_number_consistency(self.history, self.api, self.reservation_id, updated_passengers)
