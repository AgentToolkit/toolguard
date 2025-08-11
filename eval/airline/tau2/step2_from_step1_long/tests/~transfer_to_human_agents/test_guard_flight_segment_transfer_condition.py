from unittest.mock import MagicMock, patch
import pytest
from datetime import datetime, timedelta
from rt_toolguard.data_types import PolicyViolationException, ChatHistory
from airline.transfer_to_human_agents.guard_flight_segment_transfer_condition import guard_flight_segment_transfer_condition
from airline.airline_types import *
from airline.i_airline import I_Airline

class TestGuardFlightSegmentTransferCondition:
    def setup_method(self):
        # Mock chat history
        self.history = MagicMock(spec=ChatHistory)
        self.history.ask_bool.return_value = True
        self.history.did_tool_return_value.return_value = True
        self.history.was_tool_called.return_value = True

        # Mock API
        self.api = MagicMock(spec=I_Airline)

    def test_transfer_on_flown_segment(self):
        """
        Policy: "If a user requests to cancel a trip and any segments have already been flown, transfer the user to a human agent as the current tool cannot process partial trip cancellations."
        Example: "A user requests to cancel their trip, and it is found that the first segment has already been flown. The system properly transfers the user's request to a human agent since it cannot process partial trip cancellations."
        """
        # Setup reservation with two flights, first is flown
        reservation_id = "RES123"
        flight1 = ReservationFlight(flight_number="FL001", origin="JFK", destination="LAX", date=(datetime.now()-timedelta(days=2)).strftime("%Y-%m-%d"), price=300)
        flight2 = ReservationFlight(flight_number="FL002", origin="LAX", destination="SFO", date=(datetime.now()+timedelta(days=1)).strftime("%Y-%m-%d"), price=200)
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_001",
            origin="JFK",
            destination="SFO",
            flight_type="round_trip",
            cabin="economy",
            flights=[flight1, flight2],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[Payment(payment_id="PAY123", amount=500)],
            created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        self.api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        self.api.get_flight_status.side_effect = lambda fn, date: "landed" if fn == "FL001" else "available"

        summary = "User requests to cancel trip with flown segment."
        # Should transfer to human agent, not raise
        try:
            guard_flight_segment_transfer_condition(self.history, self.api, summary)
        except PolicyViolationException:
            pytest.fail("Should not raise PolicyViolationException when transfer to human agent is performed.")

    def test_transfer_on_explicit_human_request(self):
        """
        Policy: "If a user requests to cancel a trip and any segments have already been flown, transfer the user to a human agent as the current tool cannot process partial trip cancellations."
        Example: "A user explicitly requests a human agent to cancel a trip with flown segments. The system transfers to a human agent without attempting to use any tools."
        """
        # Setup reservation with flown segment
        reservation_id = "RES456"
        flight1 = ReservationFlight(flight_number="FL003", origin="ORD", destination="MIA", date=(datetime.now()-timedelta(days=1)).strftime("%Y-%m-%d"), price=400)
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_002",
            origin="ORD",
            destination="MIA",
            flight_type="one_way",
            cabin="business",
            flights=[flight1],
            passengers=[Passenger(first_name="Jane", last_name="Smith", dob="1985-05-05")],
            payment_history=[Payment(payment_id="PAY456", amount=400)],
            created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        self.api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        self.api.get_flight_status.side_effect = lambda fn, date: "landed"

        summary = "User explicitly requests human agent for cancellation."
        # Should transfer to human agent, not raise
        try:
            guard_flight_segment_transfer_condition(self.history, self.api, summary)
        except PolicyViolationException:
            pytest.fail("Should not raise PolicyViolationException when transfer to human agent is performed.")

    def test_violation_attempt_cancel_flown_segment(self):
        """
        Policy: "If a user requests to cancel a trip and any segments have already been flown, transfer the user to a human agent as the current tool cannot process partial trip cancellations."
        Example: "The user requests to cancel a trip that has already been fully or partially flown. The system attempts to process the cancellation without transferring the user to a human agent."
        """
        # Setup reservation with flown segment
        reservation_id = "RES789"
        flight1 = ReservationFlight(flight_number="FL004", origin="SEA", destination="DEN", date=(datetime.now()-timedelta(days=3)).strftime("%Y-%m-%d"), price=350)
        flight2 = ReservationFlight(flight_number="FL005", origin="DEN", destination="SEA", date=(datetime.now()+timedelta(days=2)).strftime("%Y-%m-%d"), price=350)
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_003",
            origin="SEA",
            destination="DEN",
            flight_type="round_trip",
            cabin="economy",
            flights=[flight1, flight2],
            passengers=[Passenger(first_name="Alice", last_name="Brown", dob="1992-07-07")],
            payment_history=[Payment(payment_id="PAY789", amount=700)],
            created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        self.api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        self.api.get_flight_status.side_effect = lambda fn, date: "landed" if fn == "FL004" else "available"

        summary = "System attempts to cancel trip with flown segment without transfer."
        with pytest.raises(PolicyViolationException):
            guard_flight_segment_transfer_condition(self.history, self.api, summary)

    def test_violation_no_transfer_on_flown_segment(self):
        """
        Policy: "If a user requests to cancel a trip and any segments have already been flown, transfer the user to a human agent as the current tool cannot process partial trip cancellations."
        Example: "A user asks to cancel a trip but has not explicitly requested a human agent, even though some flight segments in the trip have already been flown. The system ignores the requirement to transfer."
        """
        # Setup reservation with flown segment
        reservation_id = "RES321"
        flight1 = ReservationFlight(flight_number="FL006", origin="ATL", destination="BOS", date=(datetime.now()-timedelta(days=1)).strftime("%Y-%m-%d"), price=250)
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_004",
            origin="ATL",
            destination="BOS",
            flight_type="one_way",
            cabin="economy",
            flights=[flight1],
            passengers=[Passenger(first_name="Bob", last_name="White", dob="1980-12-12")],
            payment_history=[Payment(payment_id="PAY321", amount=250)],
            created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=0,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        self.api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        self.api.get_flight_status.side_effect = lambda fn, date: "landed"

        summary = "System ignores transfer requirement and attempts cancellation."
        with pytest.raises(PolicyViolationException):
            guard_flight_segment_transfer_condition(self.history, self.api, summary)

    def test_violation_cancel_multi_segment_with_flown(self):
        """
        Policy: "If a user requests to cancel a trip and any segments have already been flown, transfer the user to a human agent as the current tool cannot process partial trip cancellations."
        Example: "The system attempts to cancel a multi-segment trip where segments have already been flown without transferring the user to a human agent, violating the policy for partial cancellations."
        """
        # Setup reservation with multiple segments, one flown
        reservation_id = "RES654"
        flight1 = ReservationFlight(flight_number="FL007", origin="PHX", destination="LAS", date=(datetime.now()-timedelta(days=2)).strftime("%Y-%m-%d"), price=180)
        flight2 = ReservationFlight(flight_number="FL008", origin="LAS", destination="PHX", date=(datetime.now()+timedelta(days=3)).strftime("%Y-%m-%d"), price=180)
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id="user_005",
            origin="PHX",
            destination="LAS",
            flight_type="round_trip",
            cabin="basic_economy",
            flights=[flight1, flight2],
            passengers=[Passenger(first_name="Carol", last_name="Green", dob="1975-03-03")],
            payment_history=[Payment(payment_id="PAY654", amount=360)],
            created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        self.api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        self.api.get_flight_status.side_effect = lambda fn, date: "landed" if fn == "FL007" else "available"

        summary = "System attempts to cancel multi-segment trip with flown segment without transfer."
        with pytest.raises(PolicyViolationException):
            guard_flight_segment_transfer_condition(self.history, self.api, summary)
