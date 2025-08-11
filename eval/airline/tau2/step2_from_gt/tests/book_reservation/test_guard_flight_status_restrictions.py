from unittest.mock import MagicMock, patch
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.book_reservation.guard_flight_status_restrictions import guard_flight_status_restrictions
from airline.i_airline import *
from airline.airline_types import *
from datetime import datetime, timedelta

class TestGuardFlightStatusRestrictions:

    def test_compliance_booking_available_flight(self):
        """
        Policy: "Flights chosen for booking using ToolX must have the status 'available'"
        Example: "A user requests to book a flight from SFO to LAX on June 20th. The agent checks the flight information and confirms that the flight status is 'available' before proceeding with the booking using the BookReservation tool."
        """
        
        # Mock the history service
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock the API
        api = MagicMock(spec=I_Airline)
        api.get_flight_status.side_effect = lambda flight_number, date: 'available' if flight_number == "FL123" and date == "2024-06-20" else None

        # Flight and passenger details
        flights = [FlightInfo(flight_number="FL123", date="2024-06-20")]
        passengers = [Passenger(first_name="John", last_name="Doe", dob="1990-01-01")]
        payment_methods = [Payment(payment_id="pay123", amount=200)]

        # Invoke function under test
        guard_flight_status_restrictions(
            history=history,
            api=api,
            user_id="user123",
            origin="SFO",
            destination="LAX",
            flight_type="one_way",
            cabin="economy",
            flights=flights,
            passengers=passengers,
            payment_methods=payment_methods,
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no"
        )

    def test_violation_booking_delayed_flight(self):
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

        # Flight and passenger details
        flights = [FlightInfo(flight_number="FL456", date="2024-05-16")]
        passengers = [Passenger(first_name="Jane", last_name="Smith", dob="1985-05-05")]
        payment_methods = [Payment(payment_id="pay456", amount=300)]

        # Invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_flight_status_restrictions(
                history=history,
                api=api,
                user_id="user456",
                origin="ATL",
                destination="NYC",
                flight_type="one_way",
                cabin="business",
                flights=flights,
                passengers=passengers,
                payment_methods=payment_methods,
                total_baggages=2,
                nonfree_baggages=1,
                insurance="yes"
            )

    def test_violation_booking_flying_flight(self):
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

        # Flight and passenger details
        flights = [FlightInfo(flight_number="HAT007", date="2024-05-16")]
        passengers = [Passenger(first_name="Alice", last_name="Brown", dob="1992-03-03")]
        payment_methods = [Payment(payment_id="pay789", amount=400)]

        # Invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_flight_status_restrictions(
                history=history,
                api=api,
                user_id="user789",
                origin="ATL",
                destination="MIA",
                flight_type="round_trip",
                cabin="economy",
                flights=flights,
                passengers=passengers,
                payment_methods=payment_methods,
                total_baggages=3,
                nonfree_baggages=2,
                insurance="no"
            )

    def test_violation_booking_on_time_flight(self):
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

        # Flight and passenger details
        flights = [FlightInfo(flight_number="FL789", date="2024-05-16")]
        passengers = [Passenger(first_name="Bob", last_name="White", dob="1988-07-07")]
        payment_methods = [Payment(payment_id="pay321", amount=500)]

        # Invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_flight_status_restrictions(
                history=history,
                api=api,
                user_id="user321",
                origin="LAX",
                destination="DFW",
                flight_type="round_trip",
                cabin="basic_economy",
                flights=flights,
                passengers=passengers,
                payment_methods=payment_methods,
                total_baggages=4,
                nonfree_baggages=3,
                insurance="yes"
            )

    def test_violation_booking_cancelled_flight(self):
        """
        Policy: "Flights with status 'delayed', 'on time', or 'flying' cannot be booked."
        Example: "A reservation is attempted for a flight where the status is 'cancelled'. Despite knowing that only flights with 'available' status can be booked, the agent proceeds, resulting in a policy breach."
        """
        
        # Mock the history service
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock the API
        api = MagicMock(spec=I_Airline)
        api.get_flight_status.side_effect = lambda flight_number, date: 'cancelled' if flight_number == "FL654" and date == "2024-05-16" else None

        # Flight and passenger details
        flights = [FlightInfo(flight_number="FL654", date="2024-05-16")]
        passengers = [Passenger(first_name="Charlie", last_name="Green", dob="1995-09-09")]
        payment_methods = [Payment(payment_id="pay654", amount=600)]

        # Invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_flight_status_restrictions(
                history=history,
                api=api,
                user_id="user654",
                origin="LAX",
                destination="DFW",
                flight_type="round_trip",
                cabin="business",
                flights=flights,
                passengers=passengers,
                payment_methods=payment_methods,
                total_baggages=5,
                nonfree_baggages=4,
                insurance="no"
            )

    def test_violation_booking_mixed_flight_status(self):
        """
        Policy: "Flights with status 'delayed', 'on time', or 'flying' cannot be booked."
        Example: "A user attempts to make a reservation with two flights. The first one's status is 'delayed', and the second one is 'available'."
        """
        
        # Mock the history service
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock the API
        api = MagicMock(spec=I_Airline)
        api.get_flight_status.side_effect = lambda flight_number, date: 'delayed' if flight_number == "FL111" and date == "2024-05-16" else 'available' if flight_number == "FL222" and date == "2024-05-17" else None

        # Flight and passenger details
        flights = [FlightInfo(flight_number="FL111", date="2024-05-16"), FlightInfo(flight_number="FL222", date="2024-05-17")]
        passengers = [Passenger(first_name="David", last_name="Black", dob="1993-11-11")]
        payment_methods = [Payment(payment_id="pay111", amount=700)]

        # Invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_flight_status_restrictions(
                history=history,
                api=api,
                user_id="user111",
                origin="SFO",
                destination="LAX",
                flight_type="round_trip",
                cabin="economy",
                flights=flights,
                passengers=passengers,
                payment_methods=payment_methods,
                total_baggages=6,
                nonfree_baggages=5,
                insurance="yes"
            )

    def test_violation_booking_mixed_flight_status_reverse(self):
        """
        Policy: "Flights with status 'delayed', 'on time', or 'flying' cannot be booked."
        Example: "A user attempts to make a reservation with two flights. The first one's status is 'available', and the second one is 'delayed'."
        """
        
        # Mock the history service
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mock the API
        api = MagicMock(spec=I_Airline)
        api.get_flight_status.side_effect = lambda flight_number, date: 'available' if flight_number == "FL333" and date == "2024-05-16" else 'delayed' if flight_number == "FL444" and date == "2024-05-17" else None

        # Flight and passenger details
        flights = [FlightInfo(flight_number="FL333", date="2024-05-16"), FlightInfo(flight_number="FL444", date="2024-05-17")]
        passengers = [Passenger(first_name="Eve", last_name="Blue", dob="1991-12-12")]
        payment_methods = [Payment(payment_id="pay333", amount=800)]

        # Invoke function under test
        with pytest.raises(PolicyViolationException):
            guard_flight_status_restrictions(
                history=history,
                api=api,
                user_id="user333",
                origin="SFO",
                destination="LAX",
                flight_type="round_trip",
                cabin="economy",
                flights=flights,
                passengers=passengers,
                payment_methods=payment_methods,
                total_baggages=7,
                nonfree_baggages=6,
                insurance="no"
            )
