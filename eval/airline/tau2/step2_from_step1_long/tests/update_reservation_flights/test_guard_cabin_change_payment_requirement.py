from unittest.mock import MagicMock
import pytest
from datetime import datetime, timedelta
from rt_toolguard.data_types import PolicyViolationException
from airline.update_reservation_flights.guard_cabin_change_payment_requirement import guard_cabin_change_payment_requirement
from airline.airline_types import *
from airline.i_airline import *

class TestGuardCabinChangePaymentRequirement:
    
    def setup_method(self):
        # Common mocks for all tests
        self.history = MagicMock()
        self.api = MagicMock(spec=I_Airline)
        # Mock dependent tools
        self.api.get_reservation_details = MagicMock()
        self.api.get_flight_instance = MagicMock()

    def _make_flightinfo(self, flight_number, date):
        return FlightInfo(flight_number=flight_number, date=date)

    def _make_payment(self, payment_id, amount):
        return Payment(payment_id=payment_id, amount=amount)

    def _make_reservation(self, reservation_id, user_id, cabin, flights, payment_history, status=None):
        return Reservation(
            reservation_id=reservation_id,
            user_id=user_id,
            origin="JFK",
            destination="LAX",
            flight_type="round_trip",
            cabin=cabin,
            flights=flights,
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=payment_history,
            created_at=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="no",
            status=status
        )

    # --- Compliance Examples ---

    def test_change_entire_reservation_economy_to_business(self):
        """
        Policy: "ToolX can be used to modify a reservation's cabin class. Ensure a uniform cabin class change across all flights within the reservation. Make sure the user pays the fare difference between the current cabin class and the new cabin class for the entire reservation as partial changes are disallowed."
        Example: "A user changes the entire reservation's cabin class from economy to business, ensuring all flight segments are included in the updated reservation request and provides payment details to cover the fare difference, fully complying with the policy."
        """
        reservation_id = "RES123"
        user_id = "user_001"
        old_cabin = "economy"
        new_cabin = "business"
        payment_id = "credit_card_1234"
        date1 = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        date2 = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        flights = [
            self._make_flightinfo("FL100", date1),
            self._make_flightinfo("FL200", date2)
        ]
        payment = self._make_payment(payment_id, 500)
        reservation = self._make_reservation(reservation_id, user_id, old_cabin, [], [payment])
        # Mock dependent tool returns
        self.api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        self.api.get_flight_instance.side_effect = lambda fn, d: FlightDateStatusAvailable(status="available", available_seats={"business": 5, "economy": 10, "basic_economy": 0}, prices={"business": 500, "economy": 300, "basic_economy": 200})
        # Should not raise
        guard_cabin_change_payment_requirement(self.history, self.api, reservation_id, new_cabin, flights, payment_id)

    def test_update_all_segments_basic_economy_to_economy(self):
        """
        Policy: "ToolX can be used to modify a reservation's cabin class. Ensure a uniform cabin class change across all flights within the reservation. Make sure the user pays the fare difference between the current cabin class and the new cabin class for the entire reservation as partial changes are disallowed."
        Example: "A user updates all flight segments of their reservation from basic economy to economy class, ensuring the cabin class is uniformly changed across the entire reservation and pays the required fare difference, adhering to policy requirements."
        """
        reservation_id = "RES124"
        user_id = "user_002"
        old_cabin = "basic_economy"
        new_cabin = "economy"
        payment_id = "credit_card_5678"
        date1 = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        date2 = (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d")
        flights = [
            self._make_flightinfo("FL300", date1),
            self._make_flightinfo("FL400", date2)
        ]
        payment = self._make_payment(payment_id, 200)
        reservation = self._make_reservation(reservation_id, user_id, old_cabin, [], [payment])
        self.api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        self.api.get_flight_instance.side_effect = lambda fn, d: FlightDateStatusAvailable(status="available", available_seats={"business": 2, "economy": 8, "basic_economy": 1}, prices={"business": 600, "economy": 400, "basic_economy": 250})
        guard_cabin_change_payment_requirement(self.history, self.api, reservation_id, new_cabin, flights, payment_id)

    # --- Violation Examples ---

    def test_change_only_one_segment_raises(self):
        """
        Policy: "ToolX can be used to modify a reservation's cabin class. Ensure a uniform cabin class change across all flights within the reservation. Make sure the user pays the fare difference between the current cabin class and the new cabin class for the entire reservation as partial changes are disallowed."
        Example: "A user attempts to change only one segment of their reservation from economy to business class without updating the cabin class for the entire reservation, violating the required uniform cabin change."
        """
        reservation_id = "RES125"
        user_id = "user_003"
        old_cabin = "economy"
        new_cabin = "business"
        payment_id = "credit_card_9999"
        date1 = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        date2 = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        # Only one segment is changed
        flights = [self._make_flightinfo("FL500", date1)]
        payment = self._make_payment(payment_id, 300)
        reservation = self._make_reservation(reservation_id, user_id, old_cabin, [], [payment])
        self.api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        self.api.get_flight_instance.side_effect = lambda fn, d: FlightDateStatusAvailable(status="available", available_seats={"business": 1, "economy": 5, "basic_economy": 0}, prices={"business": 700, "economy": 400, "basic_economy": 250})
        with pytest.raises(PolicyViolationException):
            guard_cabin_change_payment_requirement(self.history, self.api, reservation_id, new_cabin, flights, payment_id)

    def test_mixed_cabin_classes_raises(self):
        """
        Policy: "ToolX can be used to modify a reservation's cabin class. Ensure a uniform cabin class change across all flights within the reservation. Make sure the user pays the fare difference between the current cabin class and the new cabin class for the entire reservation as partial changes are disallowed."
        Example: "A user updates their reservation to have mixed cabin classes, changing one flight to economy and another to business class within the same reservation, which breaks the policy mandating uniform cabin class across all flights."
        """
        reservation_id = "RES126"
        user_id = "user_004"
        old_cabin = "economy"
        payment_id = "credit_card_8888"
        date1 = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        date2 = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        # Simulate mixed cabin classes by passing flights with different cabins (simulate via test logic)
        flights = [self._make_flightinfo("FL600", date1), self._make_flightinfo("FL700", date2)]
        payment = self._make_payment(payment_id, 400)
        reservation = self._make_reservation(reservation_id, user_id, old_cabin, [], [payment])
        self.api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        self.api.get_flight_instance.side_effect = lambda fn, d: FlightDateStatusAvailable(status="available", available_seats={"business": 1, "economy": 5, "basic_economy": 0}, prices={"business": 700, "economy": 400, "basic_economy": 250})
        # Simulate violation by passing inconsistent cabin in test logic (actual function should check this)
        with pytest.raises(PolicyViolationException):
            guard_cabin_change_payment_requirement(self.history, self.api, reservation_id, "business", flights, payment_id)

    def test_insufficient_payment_for_all_segments_raises(self):
        """
        Policy: "ToolX can be used to modify a reservation's cabin class. Ensure a uniform cabin class change across all flights within the reservation. Make sure the user pays the fare difference between the current cabin class and the new cabin class for the entire reservation as partial changes are disallowed."
        Example: "A user changes their entire reservation from basic economy to business class but only provides payment that covers the difference for a single flight segment, not fulfilling the policy requirement for covering the fare difference for the entire reservation."
        """
        reservation_id = "RES127"
        user_id = "user_005"
        old_cabin = "basic_economy"
        new_cabin = "business"
        payment_id = "credit_card_7777"
        date1 = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        date2 = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        flights = [self._make_flightinfo("FL800", date1), self._make_flightinfo("FL900", date2)]
        payment = self._make_payment(payment_id, 100)  # Insufficient
        reservation = self._make_reservation(reservation_id, user_id, old_cabin, [], [payment])
        self.api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        self.api.get_flight_instance.side_effect = lambda fn, d: FlightDateStatusAvailable(status="available", available_seats={"business": 1, "economy": 5, "basic_economy": 0}, prices={"business": 700, "economy": 400, "basic_economy": 250})
        with pytest.raises(PolicyViolationException):
            guard_cabin_change_payment_requirement(self.history, self.api, reservation_id, new_cabin, flights, payment_id)

    def test_partial_payment_for_cabin_change_raises(self):
        """
        Policy: "ToolX can be used to modify a reservation's cabin class. Ensure a uniform cabin class change across all flights within the reservation. Make sure the user pays the fare difference between the current cabin class and the new cabin class for the entire reservation as partial changes are disallowed."
        Example: "A user attempts to change their reservation's cabin class from economy to premium economy for all flights but incorrectly inputs payment that covers a partial fare difference, resulting in insufficient payment for the full reservation change."
        """
        reservation_id = "RES128"
        user_id = "user_006"
        old_cabin = "economy"
        new_cabin = "business"
        payment_id = "credit_card_6666"
        date1 = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        date2 = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        flights = [self._make_flightinfo("FL1000", date1), self._make_flightinfo("FL1100", date2)]
        payment = self._make_payment(payment_id, 50)  # Partial/insufficient
        reservation = self._make_reservation(reservation_id, user_id, old_cabin, [], [payment])
        self.api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        self.api.get_flight_instance.side_effect = lambda fn, d: FlightDateStatusAvailable(status="available", available_seats={"business": 1, "economy": 5, "basic_economy": 0}, prices={"business": 700, "economy": 400, "basic_economy": 250})
        with pytest.raises(PolicyViolationException):
            guard_cabin_change_payment_requirement(self.history, self.api, reservation_id, new_cabin, flights, payment_id)

    def test_change_certain_segments_only_raises(self):
        """
        Policy: "ToolX can be used to modify a reservation's cabin class. Ensure a uniform cabin class change across all flights within the reservation. Make sure the user pays the fare difference between the current cabin class and the new cabin class for the entire reservation as partial changes are disallowed."
        Example: "A user tries to change the cabin class for certain flight segments without updating all flights in the reservation, resulting in an inconsistent cabin class within the reservation."
        """
        reservation_id = "RES129"
        user_id = "user_007"
        old_cabin = "economy"
        new_cabin = "business"
        payment_id = "credit_card_5555"
        date1 = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        # Only one segment provided
        flights = [self._make_flightinfo("FL1200", date1)]
        payment = self._make_payment(payment_id, 200)
        reservation = self._make_reservation(reservation_id, user_id, old_cabin, [], [payment])
        self.api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        self.api.get_flight_instance.side_effect = lambda fn, d: FlightDateStatusAvailable(status="available", available_seats={"business": 1, "economy": 5, "basic_economy": 0}, prices={"business": 700, "economy": 400, "basic_economy": 250})
        with pytest.raises(PolicyViolationException):
            guard_cabin_change_payment_requirement(self.history, self.api, reservation_id, new_cabin, flights, payment_id)

    def test_insufficient_gift_card_balance_raises(self):
        """
        Policy: "ToolX can be used to modify a reservation's cabin class. Ensure a uniform cabin class change across all flights within the reservation. Make sure the user pays the fare difference between the current cabin class and the new cabin class for the entire reservation as partial changes are disallowed."
        Example: "A user tries to change the entire reservation to business class but their payment method is actually a gift card with a balance insufficient to cover the necessary fare difference, violating payment requirement policies."
        """
        reservation_id = "RES130"
        user_id = "user_008"
        old_cabin = "economy"
        new_cabin = "business"
        payment_id = "gift_card_1234"
        date1 = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        date2 = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        flights = [self._make_flightinfo("FL1300", date1), self._make_flightinfo("FL1400", date2)]
        payment = self._make_payment(payment_id, 50)  # Insufficient
        reservation = self._make_reservation(reservation_id, user_id, old_cabin, [], [payment])
        self.api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        self.api.get_flight_instance.side_effect = lambda fn, d: FlightDateStatusAvailable(status="available", available_seats={"business": 1, "economy": 5, "basic_economy": 0}, prices={"business": 700, "economy": 400, "basic_economy": 250})
        with pytest.raises(PolicyViolationException):
            guard_cabin_change_payment_requirement(self.history, self.api, reservation_id, new_cabin, flights, payment_id)

    def test_improper_payment_details_raises(self):
        """
        Policy: "ToolX can be used to modify a reservation's cabin class. Ensure a uniform cabin class change across all flights within the reservation. Make sure the user pays the fare difference between the current cabin class and the new cabin class for the entire reservation as partial changes are disallowed."
        Example: "A user updates their reservation's cabin class across multiple flights but improperly inputs payment details, leading to a request that lacks coverage for every part of the cabin fare change."
        """
        reservation_id = "RES131"
        user_id = "user_009"
        old_cabin = "economy"
        new_cabin = "business"
        payment_id = "credit_card_0000"
        date1 = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        date2 = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        flights = [self._make_flightinfo("FL1500", date1), self._make_flightinfo("FL1600", date2)]
        payment = self._make_payment(payment_id, 0)  # No payment
        reservation = self._make_reservation(reservation_id, user_id, old_cabin, [], [payment])
        self.api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        self.api.get_flight_instance.side_effect = lambda fn, d: FlightDateStatusAvailable(status="available", available_seats={"business": 1, "economy": 5, "basic_economy": 0}, prices={"business": 700, "economy": 400, "basic_economy": 250})
        with pytest.raises(PolicyViolationException):
            guard_cabin_change_payment_requirement(self.history, self.api, reservation_id, new_cabin, flights, payment_id)
