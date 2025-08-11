from unittest.mock import MagicMock
import pytest
from datetime import datetime, timedelta
from rt_toolguard.data_types import PolicyViolationException
from airline.cancel_reservation.guard_strict_cancellation_rules_enforcement import guard_strict_cancellation_rules_enforcement
from airline.airline_types import *
from airline.i_airline import *

class TestStrictCancellationRulesEnforcement:
    
    def test_cancel_within_24_hours(self):
        """
        Policy: "All reservations can be cancelled within 24 hours of booking, or if the airline cancelled the flight. Otherwise, basic economy or economy flights can be cancelled only if travel insurance is bought and the condition is met, and business flights can always be cancelled."
        Example: "An agent checks that a reservation was booked less than 24 hours ago and cancels it accordingly, ensuring compliance with the policy."
        """
        history = MagicMock()
        reservation_id = "RES123"
        created_at = (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S")
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_1",
            origin="JFK",
            destination="LAX",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight(flight_number="FL123", origin="JFK", destination="LAX", date="2024-06-10", price=300)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[Payment(payment_id="PAY1", amount=300)],
            created_at=created_at,
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        api.get_flight_instance.side_effect = lambda flight_number, date: FlightDateStatusAvailable(status="available", available_seats={"economy": 10, "business": 5, "basic_economy": 2}, prices={"economy": 300, "business": 800, "basic_economy": 200})
        # Should not raise
        try:
            guard_strict_cancellation_rules_enforcement(history, api, reservation_id)
        except PolicyViolationException as e:
            pytest.fail(f"Cancellation within 24 hours should be allowed. Exception: {e}")

    def test_cancelled_by_airline(self):
        """
        Policy: "All reservations can be cancelled within 24 hours of booking, or if the airline cancelled the flight. Otherwise, basic economy or economy flights can be cancelled only if travel insurance is bought and the condition is met, and business flights can always be cancelled."
        Example: "An agent verifies that a flight was cancelled by the airline before executing cancellation to comply with policy rules."
        """
        history = MagicMock()
        reservation_id = "RES456"
        created_at = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S")
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_2",
            origin="JFK",
            destination="LAX",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight(flight_number="FL456", origin="JFK", destination="LAX", date="2024-06-11", price=350)],
            passengers=[Passenger(first_name="Jane", last_name="Smith", dob="1985-05-05")],
            payment_history=[Payment(payment_id="PAY2", amount=350)],
            created_at=created_at,
            total_baggages=2,
            nonfree_baggages=1,
            insurance="no",
            status=None
        )
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        api.get_flight_instance.side_effect = lambda flight_number, date: FlightDateStatusCancelled(status="cancelled")
        # Should not raise
        try:
            guard_strict_cancellation_rules_enforcement(history, api, reservation_id)
        except PolicyViolationException as e:
            pytest.fail(f"Cancellation due to airline cancellation should be allowed. Exception: {e}")

    def test_business_flight_unused(self):
        """
        Policy: "Business flights can always be cancelled if unused."
        Example: "The agent ensures a business flight reservation is entirely unused and then cancels it, complying with policy stipulations."
        """
        history = MagicMock()
        reservation_id = "RES789"
        created_at = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S")
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_3",
            origin="JFK",
            destination="LAX",
            flight_type="one_way",
            cabin="business",
            flights=[ReservationFlight(flight_number="FL789", origin="JFK", destination="LAX", date="2024-06-12", price=1000)],
            passengers=[Passenger(first_name="Alice", last_name="Brown", dob="1975-07-07")],
            payment_history=[Payment(payment_id="PAY3", amount=1000)],
            created_at=created_at,
            total_baggages=0,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        api.get_flight_instance.side_effect = lambda flight_number, date: FlightDateStatusAvailable(status="available", available_seats={"economy": 10, "business": 5, "basic_economy": 2}, prices={"economy": 300, "business": 800, "basic_economy": 200})
        # Should not raise
        try:
            guard_strict_cancellation_rules_enforcement(history, api, reservation_id)
        except PolicyViolationException as e:
            pytest.fail(f"Business flight unused should be cancellable. Exception: {e}")

    def test_cancel_with_health_insurance(self):
        """
        Policy: "Basic economy or economy flights can be cancelled only if travel insurance is bought and the condition is met."
        Example: "An agent confirms health-related travel insurance applies to a reservation due to illness and proceeds to cancel, following policy guidelines."
        """
        history = MagicMock()
        history.ask_bool.return_value = True  # Simulate insurance applies due to health
        reservation_id = "RES321"
        created_at = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S")
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_4",
            origin="JFK",
            destination="LAX",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight(flight_number="FL321", origin="JFK", destination="LAX", date="2024-06-13", price=400)],
            passengers=[Passenger(first_name="Bob", last_name="White", dob="1992-02-02")],
            payment_history=[Payment(payment_id="PAY4", amount=400)],
            created_at=created_at,
            total_baggages=1,
            nonfree_baggages=0,
            insurance="yes",
            status=None
        )
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        api.get_flight_instance.side_effect = lambda flight_number, date: FlightDateStatusAvailable(status="available", available_seats={"economy": 10, "business": 5, "basic_economy": 2}, prices={"economy": 300, "business": 800, "basic_economy": 200})
        # Should not raise
        try:
            guard_strict_cancellation_rules_enforcement(history, api, reservation_id)
        except PolicyViolationException as e:
            pytest.fail(f"Cancellation with valid health insurance should be allowed. Exception: {e}")

    def test_partial_cancellation_violation(self):
        """
        Policy: "The agent can only cancel the whole trip that is not flown. If any of the segments are already used, the agent cannot help and transfer is needed."
        Example: "The agent proceeds to cancel part of a reservation even when some segments have already been flown, which breaches the rule against partial cancellations."
        """
        history = MagicMock()
        reservation_id = "RES654"
        created_at = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S")
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_5",
            origin="JFK",
            destination="LAX",
            flight_type="round_trip",
            cabin="economy",
            flights=[
                ReservationFlight(flight_number="FL654A", origin="JFK", destination="LAX", date="2024-06-14", price=350),
                ReservationFlight(flight_number="FL654B", origin="LAX", destination="JFK", date="2024-06-20", price=350)
            ],
            passengers=[Passenger(first_name="Eve", last_name="Green", dob="1980-03-03")],
            payment_history=[Payment(payment_id="PAY5", amount=700)],
            created_at=created_at,
            total_baggages=2,
            nonfree_baggages=1,
            insurance="no",
            status=None
        )
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        # First segment flown, second not
        def get_flight_instance_side_effect(flight_number, date):
            if flight_number == "FL654A":
                return FlightDateStatusLanded(status="landed", actual_departure_time_est="2024-06-14T08:00:00", actual_arrival_time_est="2024-06-14T11:00:00")
            else:
                return FlightDateStatusAvailable(status="available", available_seats={"economy": 10, "business": 5, "basic_economy": 2}, prices={"economy": 300, "business": 800, "basic_economy": 200})
        api.get_flight_instance.side_effect = get_flight_instance_side_effect
        with pytest.raises(PolicyViolationException):
            guard_strict_cancellation_rules_enforcement(history, api, reservation_id)

    def test_cancel_without_policy_check_violation(self):
        """
        Policy: "Agents must check if reservations meet these conditions: cancelled by the airline, within 24 hours of booking, or if travel insurance applies due to health or weather. Partial cancellations are prohibited."
        Example: "An agent attempts to cancel a reservation without checking if the airline has cancelled the flight or if it's within the 24-hour booking period, violating policy conditions."
        """
        history = MagicMock()
        reservation_id = "RES987"
        created_at = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S")
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_6",
            origin="JFK",
            destination="LAX",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight(flight_number="FL987", origin="JFK", destination="LAX", date="2024-06-15", price=350)],
            passengers=[Passenger(first_name="Sam", last_name="Blue", dob="1995-04-04")],
            payment_history=[Payment(payment_id="PAY6", amount=350)],
            created_at=created_at,
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        api.get_flight_instance.side_effect = lambda flight_number, date: FlightDateStatusAvailable(status="available", available_seats={"economy": 10, "business": 5, "basic_economy": 2}, prices={"economy": 300, "business": 800, "basic_economy": 200})
        with pytest.raises(PolicyViolationException):
            guard_strict_cancellation_rules_enforcement(history, api, reservation_id)

    def test_cancel_economy_without_insurance_violation(self):
        """
        Policy: "Basic economy or economy flights can be cancelled only if travel insurance is bought and the condition is met."
        Example: "An agent cancels a reservation for a basic economy flight without verifying if travel insurance applies due to health or weather conditions."
        """
        history = MagicMock()
        reservation_id = "RES222"
        created_at = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S")
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_7",
            origin="JFK",
            destination="LAX",
            flight_type="one_way",
            cabin="basic_economy",
            flights=[ReservationFlight(flight_number="FL222", origin="JFK", destination="LAX", date="2024-06-16", price=200)],
            passengers=[Passenger(first_name="Tom", last_name="Yellow", dob="1993-06-06")],
            payment_history=[Payment(payment_id="PAY7", amount=200)],
            created_at=created_at,
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        api.get_flight_instance.side_effect = lambda flight_number, date: FlightDateStatusAvailable(status="available", available_seats={"economy": 10, "business": 5, "basic_economy": 2}, prices={"economy": 300, "business": 800, "basic_economy": 200})
        with pytest.raises(PolicyViolationException):
            guard_strict_cancellation_rules_enforcement(history, api, reservation_id)
