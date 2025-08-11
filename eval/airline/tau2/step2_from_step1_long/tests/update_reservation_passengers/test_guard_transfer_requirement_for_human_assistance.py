from unittest.mock import MagicMock
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.update_reservation_passengers.guard_transfer_requirement_for_human_assistance import guard_transfer_requirement_for_human_assistance
from airline.i_airline import I_Airline
from airline.airline_types import Reservation, Passenger

class TestGuardTransferRequirementForHumanAssistance:
    def test_update_passenger_info_no_count_change(self):
        """
        Policy: "Agents are instructed to transfer users to a human agent when passenger modification requests surpass the capabilities of the 'update_reservation_passengers' tool. This includes any change in passenger count or modifications not supported by the tool. Agents must confirm that all available tools have been used and that the issue cannot be resolved due to passenger number constraints before initiating the transfer."
        Example: "A user requests to update passenger information for a reservation, ensuring the passenger count remains unchanged, and the agent successfully uses 'update_reservation_passengers', complying with the tool's capabilities and policy requirements."
        """
        # Mock chat history
        history = MagicMock()
        # Assume all tools have been used, and the issue is not due to passenger count
        history.was_tool_called.return_value = True
        history.did_tool_return_value.return_value = True
        history.ask_bool.return_value = True

        # Mock API and reservation
        api = MagicMock(spec=I_Airline)
        reservation_id = "ZFA04Y"
        original_passengers = [
            Passenger(first_name="John", last_name="Doe", dob="1990-01-01"),
            Passenger(first_name="Jane", last_name="Smith", dob="1985-05-05")
        ]
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_123",
            origin="SFO",
            destination="JFK",
            flight_type="one_way",
            cabin="economy",
            flights=[],
            passengers=original_passengers,
            payment_history=[],
            created_at="2024-06-01T10:00:00",
            total_baggages=2,
            nonfree_baggages=1,
            insurance="no",
            status=None
        )
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None

        # New passengers (same count, info updated)
        new_passengers = [
            Passenger(first_name="John", last_name="Doe", dob="1990-01-01"),
            Passenger(first_name="Jane", last_name="Smith", dob="1985-05-05")
        ]
        # Should NOT raise
        try:
            guard_transfer_requirement_for_human_assistance(history, api, reservation_id, new_passengers)
        except PolicyViolationException as e:
            pytest.fail(f"Should not raise PolicyViolationException when passenger count is unchanged. Error: {e}")

    def test_update_passenger_details_no_count_change(self):
        """
        Policy: "Agents are instructed to transfer users to a human agent when passenger modification requests surpass the capabilities of the 'update_reservation_passengers' tool. This includes any change in passenger count or modifications not supported by the tool. Agents must confirm that all available tools have been used and that the issue cannot be resolved due to passenger number constraints before initiating the transfer."
        Example: "An agent receives a request to alter details such as contact or passport information for passengers, ensuring no change in the passenger count, and efficiently addresses it using 'update_reservation_passengers', maintaining policy compliance."
        """
        history = MagicMock()
        history.was_tool_called.return_value = True
        history.did_tool_return_value.return_value = True
        history.ask_bool.return_value = True

        api = MagicMock(spec=I_Airline)
        reservation_id = "ZFA04Y"
        original_passengers = [
            Passenger(first_name="Alice", last_name="Brown", dob="1992-03-03")
        ]
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_456",
            origin="LAX",
            destination="ORD",
            flight_type="round_trip",
            cabin="business",
            flights=[],
            passengers=original_passengers,
            payment_history=[],
            created_at="2024-06-01T10:00:00",
            total_baggages=1,
            nonfree_baggages=0,
            insurance="yes",
            status=None
        )
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None

        # New passengers (same count, details changed)
        new_passengers = [
            Passenger(first_name="Alice", last_name="Brown", dob="1992-03-03")
        ]
        try:
            guard_transfer_requirement_for_human_assistance(history, api, reservation_id, new_passengers)
        except PolicyViolationException as e:
            pytest.fail(f"Should not raise PolicyViolationException when only passenger details are changed. Error: {e}")

    def test_violation_change_passenger_count(self):
        """
        Policy: "Agents are instructed to transfer users to a human agent when passenger modification requests surpass the capabilities of the 'update_reservation_passengers' tool. This includes any change in passenger count or modifications not supported by the tool. Agents must confirm that all available tools have been used and that the issue cannot be resolved due to passenger number constraints before initiating the transfer."
        Example: "While updating a reservation, the agent attempts to change the number of passengers, such as adding an extra passenger or reducing it, without transferring the request to a human agent for assistance, thereby violating the policy."
        """
        history = MagicMock()
        history.was_tool_called.return_value = True
        history.did_tool_return_value.return_value = True
        history.ask_bool.return_value = True

        api = MagicMock(spec=I_Airline)
        reservation_id = "ZFA04Y"
        original_passengers = [
            Passenger(first_name="John", last_name="Doe", dob="1990-01-01")
        ]
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_789",
            origin="SEA",
            destination="MIA",
            flight_type="one_way",
            cabin="economy",
            flights=[],
            passengers=original_passengers,
            payment_history=[],
            created_at="2024-06-01T10:00:00",
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None

        # New passengers (count changed)
        new_passengers = [
            Passenger(first_name="John", last_name="Doe", dob="1990-01-01"),
            Passenger(first_name="New", last_name="Person", dob="2000-12-12")
        ]
        with pytest.raises(PolicyViolationException):
            guard_transfer_requirement_for_human_assistance(history, api, reservation_id, new_passengers)

    def test_violation_modify_passenger_number(self):
        """
        Policy: "Agents are instructed to transfer users to a human agent when passenger modification requests surpass the capabilities of the 'update_reservation_passengers' tool. This includes any change in passenger count or modifications not supported by the tool. Agents must confirm that all available tools have been used and that the issue cannot be resolved due to passenger number constraints before initiating the transfer."
        Example: "An agent handles a reservation update request to modify passenger numbers, such as from 3 to 6 or 6 to 8, without initiating a transfer to a human agent, which is required by the Transfer Requirement for Human Assistance policy."
        """
        history = MagicMock()
        history.was_tool_called.return_value = True
        history.did_tool_return_value.return_value = True
        history.ask_bool.return_value = True

        api = MagicMock(spec=I_Airline)
        reservation_id = "ZFA04Y"
        original_passengers = [
            Passenger(first_name="A", last_name="B", dob="1980-01-01"),
            Passenger(first_name="C", last_name="D", dob="1981-02-02"),
            Passenger(first_name="E", last_name="F", dob="1982-03-03")
        ]
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_999",
            origin="ATL",
            destination="BOS",
            flight_type="one_way",
            cabin="economy",
            flights=[],
            passengers=original_passengers,
            payment_history=[],
            created_at="2024-06-01T10:00:00",
            total_baggages=2,
            nonfree_baggages=1,
            insurance="no",
            status=None
        )
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None

        # New passengers (count changed from 3 to 6)
        new_passengers = [
            Passenger(first_name="A", last_name="B", dob="1980-01-01"),
            Passenger(first_name="C", last_name="D", dob="1981-02-02"),
            Passenger(first_name="E", last_name="F", dob="1982-03-03"),
            Passenger(first_name="G", last_name="H", dob="1990-04-04"),
            Passenger(first_name="I", last_name="J", dob="1991-05-05"),
            Passenger(first_name="K", last_name="L", dob="1992-06-06")
        ]
        with pytest.raises(PolicyViolationException):
            guard_transfer_requirement_for_human_assistance(history, api, reservation_id, new_passengers)
