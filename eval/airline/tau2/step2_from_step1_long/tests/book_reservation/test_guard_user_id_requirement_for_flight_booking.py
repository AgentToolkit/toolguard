from unittest.mock import MagicMock
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.book_reservation.guard_user_id_requirement_for_flight_booking import guard_user_id_requirement_for_flight_booking
from airline.i_airline import *
from airline.airline_types import *
from datetime import datetime, timedelta

class TestGuardUserIdRequirementForFlightBooking:
    
    def test_compliance_user_id_asked_first(self):
        """
        Policy: "The agent must first obtain the user ID before proceeding with flight booking and subsequent inquiries for trip type, origin, and destination."
        Example: "The agent asks the user for their user ID before proceeding with any inquiries on trip type, origin, destination, passenger list, and payment methods, ensuring compliance."
        """
        history = MagicMock()
        # Simulate that user_id was obtained first
        history.was_tool_called.return_value = True
        api = MagicMock(spec=I_Airline)
        user_id = "sara_doe_496"
        origin = "SFO"
        destination = "JFK"
        flight_type = "one_way"
        cabin = "economy"
        flights = [FlightInfo(flight_number="HAT001", date=(datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"))]
        passengers = [Passenger(first_name="Sara", last_name="Doe", dob="1990-04-05")]
        payment_methods = [Payment(payment_id="pay_001", amount=500)]
        total_baggages = 2
        nonfree_baggages = 1
        insurance = "no"
        # Should not raise
        try:
            guard_user_id_requirement_for_flight_booking(
                history, api, user_id, origin, destination, flight_type, cabin, flights, passengers, payment_methods, total_baggages, nonfree_baggages, insurance
            )
        except PolicyViolationException:
            pytest.fail("User ID was obtained first, but PolicyViolationException was raised.")

    def test_compliance_user_id_validated_first(self):
        """
        Policy: "The agent must first obtain the user ID before proceeding with flight booking and subsequent inquiries for trip type, origin, and destination."
        Example: "User ID is obtained and validated first, followed by inquiries about flight type, cabin class, and insurance coverage, maintaining the correct sequence as per policy."
        """
        history = MagicMock()
        history.was_tool_called.return_value = True
        api = MagicMock(spec=I_Airline)
        user_id = "john_smith_123"
        origin = "LAX"
        destination = "ORD"
        flight_type = "round_trip"
        cabin = "business"
        flights = [FlightInfo(flight_number="HAT002", date=(datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d"))]
        passengers = [Passenger(first_name="John", last_name="Smith", dob="1985-08-15")]
        payment_methods = [Payment(payment_id="pay_002", amount=1200)]
        total_baggages = 1
        nonfree_baggages = 0
        insurance = "yes"
        try:
            guard_user_id_requirement_for_flight_booking(
                history, api, user_id, origin, destination, flight_type, cabin, flights, passengers, payment_methods, total_baggages, nonfree_baggages, insurance
            )
        except PolicyViolationException:
            pytest.fail("User ID was validated first, but PolicyViolationException was raised.")

    def test_compliance_user_id_confirmed_then_flight_details(self):
        """
        Policy: "The agent must first obtain the user ID before proceeding with flight booking and subsequent inquiries for trip type, origin, and destination."
        Example: "Upon confirming the user's ID, such as 'sara_doe_496', the agent systematically handles inquiries about flight specifics, ensuring compliance through verification of user ID first."
        """
        history = MagicMock()
        history.was_tool_called.return_value = True
        api = MagicMock(spec=I_Airline)
        user_id = "sara_doe_496"
        origin = "SEA"
        destination = "BOS"
        flight_type = "one_way"
        cabin = "basic_economy"
        flights = [FlightInfo(flight_number="HAT003", date=(datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"))]
        passengers = [Passenger(first_name="Sara", last_name="Doe", dob="1990-04-05")]
        payment_methods = [Payment(payment_id="pay_003", amount=300)]
        total_baggages = 0
        nonfree_baggages = 0
        insurance = "no"
        try:
            guard_user_id_requirement_for_flight_booking(
                history, api, user_id, origin, destination, flight_type, cabin, flights, passengers, payment_methods, total_baggages, nonfree_baggages, insurance
            )
        except PolicyViolationException:
            pytest.fail("User ID was confirmed first, but PolicyViolationException was raised.")

    def test_violation_proceed_without_user_id(self):
        """
        Policy: "The agent must first obtain the user ID before proceeding with flight booking and subsequent inquiries for trip type, origin, and destination."
        Example: "The agent proceeds to book a flight without first obtaining the user ID, starting inquiries directly with the trip type, origin, and destination, which violates the policy of collecting user ID first."
        """
        history = MagicMock()
        # Simulate that user_id was NOT obtained first
        history.was_tool_called.return_value = False
        api = MagicMock(spec=I_Airline)
        user_id = ""
        origin = "SFO"
        destination = "JFK"
        flight_type = "one_way"
        cabin = "economy"
        flights = [FlightInfo(flight_number="HAT001", date=(datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"))]
        passengers = [Passenger(first_name="Sara", last_name="Doe", dob="1990-04-05")]
        payment_methods = [Payment(payment_id="pay_001", amount=500)]
        total_baggages = 2
        nonfree_baggages = 1
        insurance = "no"
        with pytest.raises(PolicyViolationException):
            guard_user_id_requirement_for_flight_booking(
                history, api, user_id, origin, destination, flight_type, cabin, flights, passengers, payment_methods, total_baggages, nonfree_baggages, insurance
            )

    def test_violation_payment_and_flight_without_user_id(self):
        """
        Policy: "The agent must first obtain the user ID before proceeding with flight booking and subsequent inquiries for trip type, origin, and destination."
        Example: "Booking is initiated with discussions about payment methods, flight details, and cabin preferences without confirming the user ID beforehand, contrary to policy requirements."
        """
        history = MagicMock()
        history.was_tool_called.return_value = False
        api = MagicMock(spec=I_Airline)
        user_id = ""
        origin = "LAX"
        destination = "ORD"
        flight_type = "round_trip"
        cabin = "business"
        flights = [FlightInfo(flight_number="HAT002", date=(datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d"))]
        passengers = [Passenger(first_name="John", last_name="Smith", dob="1985-08-15")]
        payment_methods = [Payment(payment_id="pay_002", amount=1200)]
        total_baggages = 1
        nonfree_baggages = 0
        insurance = "yes"
        with pytest.raises(PolicyViolationException):
            guard_user_id_requirement_for_flight_booking(
                history, api, user_id, origin, destination, flight_type, cabin, flights, passengers, payment_methods, total_baggages, nonfree_baggages, insurance
            )

    def test_violation_insurance_and_baggage_without_user_id(self):
        """
        Policy: "The agent must first obtain the user ID before proceeding with flight booking and subsequent inquiries for trip type, origin, and destination."
        Example: "The agent asks for insurance preferences, baggage information, and passenger count directly without verifying the user ID at the start, failing to adhere to user ID sequence policy."
        """
        history = MagicMock()
        history.was_tool_called.return_value = False
        api = MagicMock(spec=I_Airline)
        user_id = ""
        origin = "SEA"
        destination = "BOS"
        flight_type = "one_way"
        cabin = "basic_economy"
        flights = [FlightInfo(flight_number="HAT003", date=(datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"))]
        passengers = [Passenger(first_name="Sara", last_name="Doe", dob="1990-04-05")]
        payment_methods = [Payment(payment_id="pay_003", amount=300)]
        total_baggages = 0
        nonfree_baggages = 0
        insurance = "no"
        with pytest.raises(PolicyViolationException):
            guard_user_id_requirement_for_flight_booking(
                history, api, user_id, origin, destination, flight_type, cabin, flights, passengers, payment_methods, total_baggages, nonfree_baggages, insurance
            )
