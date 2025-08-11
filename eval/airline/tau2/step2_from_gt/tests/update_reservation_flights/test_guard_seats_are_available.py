from unittest.mock import MagicMock, patch
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.update_reservation_flights.guard_seats_are_available import guard_seats_are_available
from airline.i_airline import *
from airline.airline_types import *
from datetime import datetime, timedelta

class TestGuardSeatsAreAvailable:

    def test_compliance_sfo_to_lax_economy(self):
        """
        Policy: "Flights chosen for booking must have enough available seats for all passengers, and prices listed for booking."
        Example: "A user requests to book a flight from SFO to LAX on June 20th in economy class. The flight status is 'available' and there are 21 available seats"
        """
        
        # Mock the history service
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock the API
        api = MagicMock(spec=I_Airline)
        flight_info = FlightInfo(flight_number="UA123", date="2024-06-20")
        flight_status = FlightDateStatusAvailable(status="available", available_seats={"economy": 21}, prices={"economy": 200})
        api.get_flight_instance.side_effect = lambda flight_number, date: flight_status if flight_number == "UA123" and date == "2024-06-20" else None

        # Invoke function under test
        try:
            guard_seats_are_available(history, api, reservation_id="ZFA04Y", cabin="economy", flights=[flight_info], payment_id="credit_card_7815826")
        except PolicyViolationException:
            pytest.fail("Unexpected PolicyViolationException raised for compliant example.")

    def test_violation_not_enough_seats(self):
        """
        Policy: "Flights chosen for booking must have enough available seats for all passengers, and prices listed for booking."
        Example: "A user attempts to book a flight to New York on May 16th for 5 passengers in business class, however only 4 seats are available on this flight"
        """
        
        # Mock the history service
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock the API
        api = MagicMock(spec=I_Airline)
        flight_info = FlightInfo(flight_number="DL456", date="2024-05-16")
        flight_status = FlightDateStatusAvailable(status="available", available_seats={"business": 4}, prices={"business": 500})
        api.get_flight_instance.side_effect = lambda flight_number, date: flight_status if flight_number == "DL456" and date == "2024-05-16" else None

        # Invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_seats_are_available(history, api, reservation_id="ZFA04Y", cabin="business", flights=[flight_info], payment_id="credit_card_7815826")

    def test_violation_no_seats_return_flight(self):
        """
        Policy: "Flights chosen for booking must have enough available seats for all passengers, and prices listed for booking."
        Example: "An agent attempts to book a round-trip from LAX to DFW for a user in economy cabin, the outgoing flight status is available, but there are no available seats in this cabin"
        """
        
        # Mock the history service
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock the API
        api = MagicMock(spec=I_Airline)
        outgoing_flight_info = FlightInfo(flight_number="AA789", date="2024-07-10")
        return_flight_info = FlightInfo(flight_number="AA790", date="2024-07-15")
        outgoing_flight_status = FlightDateStatusAvailable(status="available", available_seats={"economy": 10}, prices={"economy": 150})
        return_flight_status = FlightDateStatusAvailable(status="available", available_seats={"economy": 0}, prices={"economy": 150})
        api.get_flight_instance.side_effect = lambda flight_number, date: (
            outgoing_flight_status if flight_number == "AA789" and date == "2024-07-10" else
            return_flight_status if flight_number == "AA790" and date == "2024-07-15" else None
        )

        # Invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_seats_are_available(history, api, reservation_id="ZFA04Y", cabin="economy", flights=[outgoing_flight_info, return_flight_info], payment_id="credit_card_7815826")
