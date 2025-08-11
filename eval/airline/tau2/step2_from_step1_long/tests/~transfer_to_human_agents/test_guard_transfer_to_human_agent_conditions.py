from unittest.mock import MagicMock
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.transfer_to_human_agents.guard_transfer_to_human_agent_conditions import guard_transfer_to_human_agent_conditions
from airline.i_airline import *
from airline.airline_types import *

class TestGuardTransferToHumanAgentConditions:
    # --- Compliance (should NOT raise) ---
    def test_transfer_on_explicit_user_request(self):
        """
        Policy: "Transfer a user to a human agent only if the user explicitly requests this transfer or if the problem cannot be resolved using available tools and policies within the scope of your actions."
        Example: "A user explicitly requests to be transferred to a human agent stating: 'I need to speak with a real person about my bill.'. The tool complies by transferring the user with the summary: 'User requests assistance with billing directly from an agent'."
        """
        history = MagicMock()
        # Simulate that the user explicitly requested a human agent
        history.ask_bool.return_value = True
        api = MagicMock(spec=I_Airline)
        summary = "User requests assistance with billing directly from an agent"
        # Should NOT raise
        try:
            guard_transfer_to_human_agent_conditions(history, api, summary)
        except PolicyViolationException as e:
            pytest.fail(f"Explicit user request should allow transfer. Unexpected PolicyViolationException: {e}")

    def test_transfer_when_no_tool_can_resolve(self):
        """
        Policy: "Transfer a user to a human agent only if the user explicitly requests this transfer or if the problem cannot be resolved using available tools and policies within the scope of your actions."
        Example: "The user requests information on a flight destination that is not covered by the available tools as it includes airports outside the supported database. Given that no tool can resolve this, the tool transfers the user with the summary 'User seeks flight info for unsupported airports', adhering to policy."
        """
        history = MagicMock()
        # Simulate that the issue cannot be resolved by available tools
        history.ask_bool.return_value = False
        history.was_tool_called.return_value = False
        api = MagicMock(spec=I_Airline)
        summary = "User seeks flight info for unsupported airports"
        # Should NOT raise
        try:
            guard_transfer_to_human_agent_conditions(history, api, summary)
        except PolicyViolationException as e:
            pytest.fail(f"Unresolvable issue should allow transfer. Unexpected PolicyViolationException: {e}")

    # --- Violation (should raise) ---
    def test_transfer_without_attempting_tool(self):
        """
        Policy: "Transfer a user to a human agent only if the user explicitly requests this transfer or if the problem cannot be resolved using available tools and policies within the scope of your actions."
        Example: "A user asks for details about their reservation ID '8JX2WO'. Without attempting to retrieve the reservation details using `get_reservation_details`, the tool transfers the user to a human agent with the summary: 'User requests reservation details'. This violates the policy as the issue can be resolved with the available tool."
        """
        history = MagicMock()
        # Simulate that the user did NOT explicitly request a human agent
        history.ask_bool.return_value = False
        # Simulate that the tool to resolve the issue was NOT called
        history.was_tool_called.return_value = False
        api = MagicMock(spec=I_Airline)
        summary = "User requests reservation details"
        with pytest.raises(PolicyViolationException):
            guard_transfer_to_human_agent_conditions(history, api, summary)

    def test_transfer_without_using_update_reservation(self):
        """
        Policy: "Transfer a user to a human agent only if the user explicitly requests this transfer or if the problem cannot be resolved using available tools and policies within the scope of your actions."
        Example: "The user wanted to update their reservation with ID 'ZFA04Y' to reflect a change in flight dates. Instead of using `update_reservation_flights`, the tool transfers the user to a human agent with the summary: 'User requests flight date change'. The policy is violated as the available tools can handle the request."
        """
        history = MagicMock()
        history.ask_bool.return_value = False
        history.was_tool_called.return_value = False
        api = MagicMock(spec=I_Airline)
        summary = "User requests flight date change"
        with pytest.raises(PolicyViolationException):
            guard_transfer_to_human_agent_conditions(history, api, summary)

    def test_transfer_for_simple_calculation(self):
        """
        Policy: "Transfer a user to a human agent only if the user explicitly requests this transfer or if the problem cannot be resolved using available tools and policies within the scope of your actions."
        Example: "A user asks for a human agent but is looking to calculate a simple mathematical expression '3 * 8 + (5 - 1)' that can be resolved using the `calculate` tool. The tool transfers the user without checking that the issue can be resolved internally, violating the policy requirement."
        """
        history = MagicMock()
        history.ask_bool.return_value = False
        history.was_tool_called.return_value = False
        api = MagicMock(spec=I_Airline)
        summary = "User requests calculation assistance"
        with pytest.raises(PolicyViolationException):
            guard_transfer_to_human_agent_conditions(history, api, summary)

    def test_transfer_for_airport_listing(self):
        """
        Policy: "Transfer a user to a human agent only if the user explicitly requests this transfer or if the problem cannot be resolved using available tools and policies within the scope of your actions."
        Example: "The tool transfers a user asking for airport listings to a human agent with the summary 'User requests list of airports'. This violates the policy as the tool `list_all_airports` can be used to solve the issue."
        """
        history = MagicMock()
        history.ask_bool.return_value = False
        history.was_tool_called.return_value = False
        api = MagicMock(spec=I_Airline)
        summary = "User requests list of airports"
        with pytest.raises(PolicyViolationException):
            guard_transfer_to_human_agent_conditions(history, api, summary)

    def test_transfer_for_flight_status_without_check(self):
        """
        Policy: "Transfer a user to a human agent only if the user explicitly requests this transfer or if the problem cannot be resolved using available tools and policies within the scope of your actions."
        Example: "A user is transferred to a human agent upon asking for the status of a flight number 'AA123' on a specific date '2024-01-01', without attempting to use `get_flight_status`. This violates the policy as the available tool can resolve the issue."
        """
        history = MagicMock()
        history.ask_bool.return_value = False
        history.was_tool_called.return_value = False
        api = MagicMock(spec=I_Airline)
        summary = "User requests flight status for AA123 on 2024-01-01"
        with pytest.raises(PolicyViolationException):
            guard_transfer_to_human_agent_conditions(history, api, summary)
