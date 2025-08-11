from unittest.mock import MagicMock
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.transfer_to_human_agents.guard_human_agent_assistance_limitation import guard_human_agent_assistance_limitation
from airline.i_airline import *
from airline.airline_types import *

class TestHumanAgentAssistanceLimitation:
    
    def test_update_passenger_details_no_transfer(self):
        """
        Policy: For requests involving changes to the number of passengers in a reservation, notify the user that neither the automated system nor human agents can process this change. Therefore, transfer to a human agent is not permitted for these requests.
        Example: "A user requests to update passenger details without changing the number of passengers and is not transferred to a human agent since the tool can handle the modification, adhering to the policy."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        summary = "Update passenger passport details for reservation 12345."
        # Should not raise PolicyViolationException
        try:
            guard_human_agent_assistance_limitation(history, api, summary)
        except PolicyViolationException:
            pytest.fail("Should not raise PolicyViolationException when only updating passenger details without changing count.")

    def test_modify_passport_details_no_transfer(self):
        """
        Policy: For requests involving changes to the number of passengers in a reservation, notify the user that neither the automated system nor human agents can process this change. Therefore, transfer to a human agent is not permitted for these requests.
        Example: "The user asks to modify passport details for existing passengers, and the system performs the update without any transfer, as passenger count remains unchanged."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        summary = "Modify passport details for all passengers in reservation 67890."
        try:
            guard_human_agent_assistance_limitation(history, api, summary)
        except PolicyViolationException:
            pytest.fail("Should not raise PolicyViolationException when modifying passport details for existing passengers.")

    def test_change_seat_preferences_no_transfer(self):
        """
        Policy: For requests involving changes to the number of passengers in a reservation, notify the user that neither the automated system nor human agents can process this change. Therefore, transfer to a human agent is not permitted for these requests.
        Example: "A user needs to change seat preferences for the same number of passengers in a reservation. The automated system successfully handles this request as it does not involve altering passenger count, complying with the policy."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        summary = "Change seat preferences for all passengers in reservation ABCDE."
        try:
            guard_human_agent_assistance_limitation(history, api, summary)
        except PolicyViolationException:
            pytest.fail("Should not raise PolicyViolationException when changing seat preferences for the same number of passengers.")

    def test_change_arrival_time_preferences_no_transfer(self):
        """
        Policy: For requests involving changes to the number of passengers in a reservation, notify the user that neither the automated system nor human agents can process this change. Therefore, transfer to a human agent is not permitted for these requests.
        Example: "A user wants to change the arrival time preferences for existing passengers in a reservation without changing the number of passengers. This update is handled by the automated system, in alignment with the policy."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        summary = "Change arrival time preferences for reservation FGHIJ."
        try:
            guard_human_agent_assistance_limitation(history, api, summary)
        except PolicyViolationException:
            pytest.fail("Should not raise PolicyViolationException when changing arrival time preferences for existing passengers.")

    def test_modify_contact_info_no_transfer(self):
        """
        Policy: For requests involving changes to the number of passengers in a reservation, notify the user that neither the automated system nor human agents can process this change. Therefore, transfer to a human agent is not permitted for these requests.
        Example: "The user requests to modify the contact information of current passengers in the booking. Since the number of passengers remains the same, the automated system processes the update, complying with the policy without transferring to a human agent."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        summary = "Update contact information for all passengers in reservation KLMNO."
        try:
            guard_human_agent_assistance_limitation(history, api, summary)
        except PolicyViolationException:
            pytest.fail("Should not raise PolicyViolationException when modifying contact information for current passengers.")

    def test_change_number_of_passengers_raises(self):
        """
        Policy: For requests involving changes to the number of passengers in a reservation, notify the user that neither the automated system nor human agents can process this change. Therefore, transfer to a human agent is not permitted for these requests.
        Example: "A user requests to change the number of passengers in a reservation and since it cannot be done via the automated system, the user is transferred to a human agent, violating the policy."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        summary = "Change number of passengers from 2 to 3 in reservation 24680."
        with pytest.raises(PolicyViolationException):
            guard_human_agent_assistance_limitation(history, api, summary)

    def test_add_passenger_and_transfer_raises(self):
        """
        Policy: For requests involving changes to the number of passengers in a reservation, notify the user that neither the automated system nor human agents can process this change. Therefore, transfer to a human agent is not permitted for these requests.
        Example: "The user attempts to modify from five to six passengers in their reservation and, despite being impossible both automatically and manually, they are incorrectly transferred to a human agent for assistance, contrary to policy restrictions."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        summary = "Add a passenger to reservation with 5 passengers."
        with pytest.raises(PolicyViolationException):
            guard_human_agent_assistance_limitation(history, api, summary)

    def test_transfer_after_additional_passenger_raises(self):
        """
        Policy: For requests involving changes to the number of passengers in a reservation, notify the user that neither the automated system nor human agents can process this change. Therefore, transfer to a human agent is not permitted for these requests.
        Example: "A customer is transferred to a human agent after attempting to add an additional passenger to their booking, which the policy clearly prohibits."
        """
        history = MagicMock()
        api = MagicMock(spec=I_Airline)
        summary = "Customer requests transfer to human agent after trying to add a passenger."
        with pytest.raises(PolicyViolationException):
            guard_human_agent_assistance_limitation(history, api, summary)
