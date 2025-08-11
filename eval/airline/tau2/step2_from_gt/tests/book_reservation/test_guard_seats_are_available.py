from unittest.mock import MagicMock, patch
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.book_reservation.guard_seats_are_available import guard_seats_are_available
from airline.i_airline import *
from datetime import datetime, timedelta

class TestGuardSeatsAreAvailable:

    def test_compliance_booking_economy_class(self):
        """
        Policy: "Flights chosen for booking must have enough available seats for all passengers, and prices listed for booking."
        Example: "A user requests to book a flight from SFO to LAX on June 20th in economy class. The flight status is 'available' and there are 21 available seats"
        """
        
        # mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True

        # mock the API
        api = MagicMock(spec=I_Airline)
        flight_status = FlightDateStatusAvailable(status='available', available_seats={'economy': 21}, prices={'economy': 300})
        api.get_flight_instance.side_effect = lambda flight_number, date: flight_status if flight_number == "FL123" and date == "2024-06-20" else None

        flights = [FlightInfo(flight_number="FL123", date="2024-06-20")]
        passengers = [Passenger(first_name="John", last_name="Doe", dob="1990-01-01")]
        payment_methods = [Payment(payment_id="pay123", amount=300)]

        # invoke function under test
        guard_seats_are_available(history, api, user_id="user123", origin="SFO", destination="LAX", flight_type="one_way", cabin="economy", flights=flights, passengers=passengers, payment_methods=payment_methods, total_baggages=1, nonfree_baggages=0, insurance="no")

    def test_violation_not_enough_seats(self):
        """
        Policy: "Flights chosen for booking must have enough available seats for all passengers, and prices listed for booking."
        Example: "A user attempts to book a flight to New York on May 16th for 5 passengers in business class, however only 4 seats are available on this flight"
        """
        
        # mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True

        # mock the API
        api = MagicMock(spec=I_Airline)
        flight_status = FlightDateStatusAvailable(status='available', available_seats={'business': 4}, prices={'business': 1000})
        api.get_flight_instance.side_effect = lambda flight_number, date: flight_status if flight_number == "FL456" and date == "2024-05-16" else None

        flights = [FlightInfo(flight_number="FL456", date="2024-05-16")]
        passengers = [Passenger(first_name="Alice", last_name="Smith", dob="1985-05-05") for _ in range(5)]
        payment_methods = [Payment(payment_id="pay456", amount=5000)]

        # invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_seats_are_available(history, api, user_id="user456", origin="SFO", destination="JFK", flight_type="one_way", cabin="business", flights=flights, passengers=passengers, payment_methods=payment_methods, total_baggages=5, nonfree_baggages=2, insurance="yes")

    def test_violation_no_available_seats_return_flight(self):
        """
        Policy: "Flights chosen for booking must have enough available seats for all passengers, and prices listed for booking."
        Example: "An agent attempts to book a round-trip from LAX to DFW for a user in economy cabin, the outgoing flight status is available, but there are no available seats in this cabin"
        """
        
        # mock the history service:
        history = MagicMock()
        history.ask_bool.return_value = True

        # mock the API
        api = MagicMock(spec=I_Airline)
        outgoing_flight_status = FlightDateStatusAvailable(status='available', available_seats={'economy': 10}, prices={'economy': 200})
        return_flight_status = FlightDateStatusAvailable(status='available', available_seats={'economy': 0}, prices={'economy': 200})
        api.get_flight_instance.side_effect = lambda flight_number, date: outgoing_flight_status if flight_number == "FL789" and date == "2024-07-01" else return_flight_status if flight_number == "FL790" and date == "2024-07-10" else None

        flights = [FlightInfo(flight_number="FL789", date="2024-07-01"), FlightInfo(flight_number="FL790", date="2024-07-10")]
        passengers = [Passenger(first_name="Bob", last_name="Brown", dob="1975-03-03")]
        payment_methods = [Payment(payment_id="pay789", amount=400)]

        # invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_seats_are_available(history, api, user_id="user789", origin="LAX", destination="DFW", flight_type="round_trip", cabin="economy", flights=flights, passengers=passengers, payment_methods=payment_methods, total_baggages=1, nonfree_baggages=0, insurance="no")
