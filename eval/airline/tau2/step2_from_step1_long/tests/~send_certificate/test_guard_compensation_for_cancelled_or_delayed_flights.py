from unittest.mock import MagicMock
import pytest
from datetime import datetime, timedelta
from rt_toolguard.data_types import PolicyViolationException
from airline.send_certificate.guard_compensation_for_cancelled_or_delayed_flights import guard_compensation_for_cancelled_or_delayed_flights
from airline.airline_types import *
from airline.i_airline import *

class TestCompensationForCancelledOrDelayedFlights:
    # --- COMPLIANCE EXAMPLES ---
    def test_silver_member_cancelled_flight_100_per_passenger(self):
        """
        Policy: "Agents can issue compensation certificates using the `send_certificate` tool, but only for users who meet specific eligibility criteria: they must be silver/gold members, have travel insurance, or travel in business class. Compensation amounts are $100 per passenger for cancellations."
        Example: "After a silver member complains about their flight being canceled, the agent verifies membership and sends a certificate of $100 per passenger to the two passengers in the reservation."
        """
        history = MagicMock()
        history.ask_bool.return_value = True  # User complained and requested compensation
        history.was_tool_called.return_value = True
        history.did_tool_return_value.return_value = True

        user_id = "silver_user_001"
        reservation_id = "RES12345"
        flight_number = "FL1001"
        flight_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        passengers = [
            Passenger(first_name="Alice", last_name="Smith", dob="1990-01-01"),
            Passenger(first_name="Bob", last_name="Smith", dob="1992-02-02")
        ]
        user = User(
            user_id=user_id,
            name=Name(first_name="Alice", last_name="Smith"),
            address=Address(address1="123 Main St", address2=None, city="NYC", country="USA", state="NY", zip="10001"),
            email="alice@example.com",
            dob="1990-01-01",
            payment_methods={},
            saved_passengers=[],
            membership="silver",
            reservations=[reservation_id]
        )
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id=user_id,
            origin="JFK",
            destination="LAX",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight(flight_number=flight_number, origin="JFK", destination="LAX", date=flight_date, price=300)],
            passengers=passengers,
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=0,
            insurance="no",
            status="cancelled"
        )
        flight_status = "cancelled"

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda uid: user if uid == user_id else None
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        api.get_flight_status.side_effect = lambda fn, dt: flight_status if fn == flight_number and dt == flight_date else "on time"

        amount = 100 * len(passengers)
        # Should NOT raise
        guard_compensation_for_cancelled_or_delayed_flights(history, api, user_id, amount)

    def test_gold_member_with_insurance_delayed_flight_50_per_passenger(self):
        """
        Policy: "Compensation amounts are $50 per passenger for delays if the reservation is altered as requested by the user."
        Example: "The agent checks the user profile and confirms the user is a gold member with travel insurance who has just experienced a flight delay, and has requested a reservation change, thus issuing a certificate of $50 per passenger for the three passengers."
        """
        history = MagicMock()
        history.ask_bool.return_value = True  # User complained and requested compensation
        history.was_tool_called.return_value = True
        history.did_tool_return_value.return_value = True

        user_id = "gold_user_002"
        reservation_id = "RES67890"
        flight_number = "FL2002"
        flight_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        passengers = [
            Passenger(first_name="Carol", last_name="Jones", dob="1985-03-03"),
            Passenger(first_name="Dave", last_name="Jones", dob="1987-04-04"),
            Passenger(first_name="Eve", last_name="Jones", dob="1990-05-05")
        ]
        user = User(
            user_id=user_id,
            name=Name(first_name="Carol", last_name="Jones"),
            address=Address(address1="456 Elm St", address2=None, city="LA", country="USA", state="CA", zip="90001"),
            email="carol@example.com",
            dob="1985-03-03",
            payment_methods={},
            saved_passengers=[],
            membership="gold",
            reservations=[reservation_id]
        )
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id=user_id,
            origin="LAX",
            destination="ORD",
            flight_type="round_trip",
            cabin="economy",
            flights=[ReservationFlight(flight_number=flight_number, origin="LAX", destination="ORD", date=flight_date, price=400)],
            passengers=passengers,
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=20)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=3,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )
        flight_status = "delayed"

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda uid: user if uid == user_id else None
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        api.get_flight_status.side_effect = lambda fn, dt: flight_status if fn == flight_number and dt == flight_date else "on time"

        amount = 50 * len(passengers)
        # Should NOT raise
        guard_compensation_for_cancelled_or_delayed_flights(history, api, user_id, amount)

    def test_business_class_cancellation_100_per_passenger(self):
        """
        Policy: "Agents can issue compensation certificates using the `send_certificate` tool, but only for users who meet specific eligibility criteria: they must be silver/gold members, have travel insurance, or travel in business class. Compensation amounts are $100 per passenger for cancellations."
        Example: "A user, traveling in business class, complains about a flight cancellation. The agent verifies this and issues a $100 certificate per passenger after confirming the cancellation, following the policy's eligibility criteria."
        """
        history = MagicMock()
        history.ask_bool.return_value = True
        history.was_tool_called.return_value = True
        history.did_tool_return_value.return_value = True

        user_id = "biz_user_003"
        reservation_id = "RES24680"
        flight_number = "FL3003"
        flight_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        passengers = [Passenger(first_name="Frank", last_name="Miller", dob="1975-06-06")]
        user = User(
            user_id=user_id,
            name=Name(first_name="Frank", last_name="Miller"),
            address=Address(address1="789 Oak St", address2=None, city="Chicago", country="USA", state="IL", zip="60601"),
            email="frank@example.com",
            dob="1975-06-06",
            payment_methods={},
            saved_passengers=[],
            membership="regular",
            reservations=[reservation_id]
        )
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id=user_id,
            origin="ORD",
            destination="JFK",
            flight_type="one_way",
            cabin="business",
            flights=[ReservationFlight(flight_number=flight_number, origin="ORD", destination="JFK", date=flight_date, price=500)],
            passengers=passengers,
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status="cancelled"
        )
        flight_status = "cancelled"

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda uid: user if uid == user_id else None
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        api.get_flight_status.side_effect = lambda fn, dt: flight_status if fn == flight_number and dt == flight_date else "on time"

        amount = 100 * len(passengers)
        guard_compensation_for_cancelled_or_delayed_flights(history, api, user_id, amount)

    # --- VIOLATION EXAMPLES ---
    def test_regular_member_no_insurance_economy_cancellation_should_raise(self):
        """
        Policy: "Do not compensate if the user is regular member and has no travel insurance and flies (basic) economy."
        Example: "An agent tries to send a $100 compensation certificate for a canceled flight to a regular member who does not have travel insurance and is traveling in basic economy class, violating the eligibility criteria."
        """
        history = MagicMock()
        history.ask_bool.return_value = True
        history.was_tool_called.return_value = True
        history.did_tool_return_value.return_value = True

        user_id = "reg_user_004"
        reservation_id = "RES13579"
        flight_number = "FL4004"
        flight_date = (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d")
        passengers = [Passenger(first_name="Grace", last_name="Lee", dob="1980-07-07")]
        user = User(
            user_id=user_id,
            name=Name(first_name="Grace", last_name="Lee"),
            address=Address(address1="321 Pine St", address2=None, city="Boston", country="USA", state="MA", zip="02101"),
            email="grace@example.com",
            dob="1980-07-07",
            payment_methods={},
            saved_passengers=[],
            membership="regular",
            reservations=[reservation_id]
        )
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id=user_id,
            origin="BOS",
            destination="MIA",
            flight_type="one_way",
            cabin="basic_economy",
            flights=[ReservationFlight(flight_number=flight_number, origin="BOS", destination="MIA", date=flight_date, price=200)],
            passengers=passengers,
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=40)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status="cancelled"
        )
        flight_status = "cancelled"

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda uid: user if uid == user_id else None
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        api.get_flight_status.side_effect = lambda fn, dt: flight_status if fn == flight_number and dt == flight_date else "on time"

        amount = 100 * len(passengers)
        with pytest.raises(PolicyViolationException, match="User is not eligible for compensation: must be silver/gold member, have insurance, or travel in business class"):
            guard_compensation_for_cancelled_or_delayed_flights(history, api, user_id, amount)

    def test_compensation_for_delay_without_eligibility_should_raise(self):
        """
        Policy: "Do not compensate if the user is regular member and has no travel insurance and flies (basic) economy."
        Example: "An agent issues a compensation certificate of $50 for flight delay without confirming the user is traveling in business class, has travel insurance, or membership status and fails to verify if a reservation change was requested."
        """
        history = MagicMock()
        history.ask_bool.return_value = True
        history.was_tool_called.return_value = True
        history.did_tool_return_value.return_value = True

        user_id = "reg_user_005"
        reservation_id = "RES11223"
        flight_number = "FL5005"
        flight_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        passengers = [Passenger(first_name="Henry", last_name="Kim", dob="1995-08-08")]
        user = User(
            user_id=user_id,
            name=Name(first_name="Henry", last_name="Kim"),
            address=Address(address1="654 Cedar St", address2=None, city="Seattle", country="USA", state="WA", zip="98101"),
            email="henry@example.com",
            dob="1995-08-08",
            payment_methods={},
            saved_passengers=[],
            membership="regular",
            reservations=[reservation_id]
        )
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id=user_id,
            origin="SEA",
            destination="DEN",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight(flight_number=flight_number, origin="SEA", destination="DEN", date=flight_date, price=250)],
            passengers=passengers,
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=50)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )
        flight_status = "delayed"

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda uid: user if uid == user_id else None
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        api.get_flight_status.side_effect = lambda fn, dt: flight_status if fn == flight_number and dt == flight_date else "on time"

        amount = 50 * len(passengers)
        with pytest.raises(PolicyViolationException, match="User is not eligible for compensation: must be silver/gold member, have insurance, or travel in business class"):
            guard_compensation_for_cancelled_or_delayed_flights(history, api, user_id, amount)

    def test_certificate_sent_without_complaint_should_raise(self):
        """
        Policy: "Do not proactively offer these unless the user complains about the situation and explicitly asks for some compensation."
        Example: "A certificate is sent to a user without verifying their eligibility. The user is neither a silver/gold member nor has travel insurance, traveling in economy, and did not complain about the canceled flight, which is a breach of policy requirements."
        """
        history = MagicMock()
        history.ask_bool.return_value = False  # User did NOT complain
        history.was_tool_called.return_value = False
        history.did_tool_return_value.return_value = False

        user_id = "reg_user_006"
        reservation_id = "RES33445"
        flight_number = "FL6006"
        flight_date = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")
        passengers = [Passenger(first_name="Ivy", last_name="Nguyen", dob="1988-09-09")]
        user = User(
            user_id=user_id,
            name=Name(first_name="Ivy", last_name="Nguyen"),
            address=Address(address1="987 Spruce St", address2=None, city="Houston", country="USA", state="TX", zip="77001"),
            email="ivy@example.com",
            dob="1988-09-09",
            payment_methods={},
            saved_passengers=[],
            membership="regular",
            reservations=[reservation_id]
        )
        reservation = Reservation(
            reservation_id=reservation_id,
            user_id=user_id,
            origin="IAH",
            destination="ATL",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight(flight_number=flight_number, origin="IAH", destination="ATL", date=flight_date, price=180)],
            passengers=passengers,
            payment_history=[],
            created_at=(datetime.now() - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status="cancelled"
        )
        flight_status = "cancelled"

        api = MagicMock(spec=I_Airline)
        api.get_user_details.side_effect = lambda uid: user if uid == user_id else None
        api.get_reservation_details.side_effect = lambda rid: reservation if rid == reservation_id else None
        api.get_flight_status.side_effect = lambda fn, dt: flight_status if fn == flight_number and dt == flight_date else "on time"

        amount = 100 * len(passengers)
        with pytest.raises(PolicyViolationException, match="User did not complain or request compensation"):
            guard_compensation_for_cancelled_or_delayed_flights(history, api, user_id, amount)
