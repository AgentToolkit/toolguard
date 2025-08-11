from unittest.mock import MagicMock, patch
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.update_reservation_flights.guard_flight_status_restrictions import guard_flight_status_restrictions
from airline.i_airline import *
from airline.airline_types import *
from datetime import datetime, timedelta

class TestGuardFlightStatusRestrictions:

    def test_compliance_flight_status_available(self):
        """
        Policy: "Flights chosen for booking using ToolX must have the status 'available' to ensure that they have not taken off."
        Example: "A user requests to book a flight from SFO to LAX on June 20th. The agent checks the flight information and confirms that the flight status is 'available' before proceeding with the booking using the BookReservation tool."
        """
        
        # Mock the history service
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock the API
        api = MagicMock(spec=I_Airline)
        api.get_flight_status.side_effect = lambda flight_number, date: 'available' if flight_number == "FL123" and date == "2024-06-20" else None

        # Flight info
        flight_info = FlightInfo(flight_number="FL123", date="2024-06-20")

        # Invoke function under test
        try:
            guard_flight_status_restrictions(history, api, "RES123", "economy", [flight_info], "credit_card_123")
        except PolicyViolationException:
            pytest.fail("PolicyViolationException was raised unexpectedly for a compliant flight status.")

    def test_violation_flight_status_delayed(self):
        """
        Policy: "Flights with status 'delayed', 'on time', or 'flying' cannot be booked."
        Example: "A user attempts to book a flight to New York on May 16th using the BookReservation tool. However, the flight status indicates 'delayed'."
        """
        
        # Mock the history service
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock the API
        api = MagicMock(spec=I_Airline)
        api.get_flight_status.side_effect = lambda flight_number, date: 'delayed' if flight_number == "FL456" and date == "2024-05-16" else None

        # Flight info
        flight_info = FlightInfo(flight_number="FL456", date="2024-05-16")

        # Invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_flight_status_restrictions(history, api, "RES456", "economy", [flight_info], "credit_card_456")

    def test_violation_flight_status_flying(self):
        """
        Policy: "Flights with status 'delayed', 'on time', or 'flying' cannot be booked."
        Example: "An agent tries to book a reservation for a user on flight HAT007 from ATL to MIA. The API checks reveal that the flight's status is currently 'flying'."
        """
        
        # Mock the history service
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock the API
        api = MagicMock(spec=I_Airline)
        api.get_flight_status.side_effect = lambda flight_number, date: 'flying' if flight_number == "HAT007" and date == "2024-05-16" else None

        # Flight info
        flight_info = FlightInfo(flight_number="HAT007", date="2024-05-16")

        # Invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_flight_status_restrictions(history, api, "RES789", "business", [flight_info], "credit_card_789")

    def test_violation_flight_status_on_time(self):
        """
        Policy: "Flights with status 'delayed', 'on time', or 'flying' cannot be booked."
        Example: "A reservation request is made for a flight with the status 'on time'."
        """
        
        # Mock the history service
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock the API
        api = MagicMock(spec=I_Airline)
        api.get_flight_status.side_effect = lambda flight_number, date: 'on time' if flight_number == "FL789" and date == "2024-05-16" else None

        # Flight info
        flight_info = FlightInfo(flight_number="FL789", date="2024-05-16")

        # Invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_flight_status_restrictions(history, api, "RES101", "economy", [flight_info], "credit_card_101")
