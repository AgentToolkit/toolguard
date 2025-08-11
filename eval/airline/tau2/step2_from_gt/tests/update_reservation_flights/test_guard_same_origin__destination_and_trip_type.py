from unittest.mock import MagicMock, patch
import pytest
from rt_toolguard.data_types import PolicyViolationException
from airline.update_reservation_flights.guard_same_origin__destination_and_trip_type import guard_same_origin__destination_and_trip_type
from airline.i_airline import *
from airline.airline_types import *
from datetime import datetime, timedelta

class TestGuardSameOriginDestinationAndTripType:

    def test_change_date_one_way_economy_reservation(self):
        """
        Policy: "non-basic-economy reservation can be modified without changing the origin, destination, and trip type"
        Example: "change the date of one-way economy reservation."
        """
        
        history = MagicMock()
        history.ask_bool.return_value = True

        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="sara_doe_496",
            origin="JFK",
            destination="LAX",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight(flight_number="HAT001", origin="JFK", destination="LAX", date="2024-05-01", price=300)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=300)],
            created_at=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None

        flights = [FlightInfo(flight_number="HAT001", date="2024-05-02")]

        guard_same_origin__destination_and_trip_type(history, api, "ZFA04Y", "economy", flights, "credit_card_7815826")

    def test_change_flight_one_way_economy_reservation_same_origin_destination_date(self):
        """
        Policy: "non-basic-economy reservation can be modified without changing the origin, destination, and trip type"
        Example: "change the flight of one-way economy reservation, keeping the same origin, destination and date."
        """
        
        history = MagicMock()
        history.ask_bool.return_value = True

        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="sara_doe_496",
            origin="JFK",
            destination="LAX",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight(flight_number="HAT002", origin="JFK", destination="LAX", date="2024-05-01", price=300)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=300)],
            created_at=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None

        flights = [FlightInfo(flight_number="HAT002", date="2024-05-01")]

        guard_same_origin__destination_and_trip_type(history, api, "ZFA04Y", "economy", flights, "credit_card_7815826")

    def test_change_business_class_one_way_reservation_two_legs(self):
        """
        Policy: "non-basic-economy reservation can be modified without changing the origin, destination, and trip type"
        Example: "change a business classs one way reservation with two flight legs: JFK-LAX, LAX-SFO, to : JFK-SFO."
        """
        
        history = MagicMock()
        history.ask_bool.return_value = True

        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="sara_doe_496",
            origin="JFK",
            destination="SFO",
            flight_type="one_way",
            cabin="business",
            flights=[ReservationFlight(flight_number="HAT003", origin="JFK", destination="SFO", date="2024-05-01", price=1000)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=1000)],
            created_at=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None

        flights = [FlightInfo(flight_number="HAT003", date="2024-05-01")]

        guard_same_origin__destination_and_trip_type(history, api, "ZFA04Y", "business", flights, "credit_card_7815826")

    def test_change_economy_class_one_way_reservation_two_legs(self):
        """
        Policy: "non-basic-economy reservation can be modified without changing the origin, destination, and trip type"
        Example: "change an economy classs one way reservation with two flight legs: JFK-LAX, LAX-SFO, to : JFK-TLV, TLV-SFO."
        """
        
        history = MagicMock()
        history.ask_bool.return_value = True

        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="sara_doe_496",
            origin="JFK",
            destination="SFO",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight(flight_number="HAT004", origin="JFK", destination="SFO", date="2024-05-01", price=500)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=500)],
            created_at=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None

        flights = [FlightInfo(flight_number="HAT004", date="2024-05-01")]

        guard_same_origin__destination_and_trip_type(history, api, "ZFA04Y", "economy", flights, "credit_card_7815826")

    def test_change_economy_class_round_trip_reservation(self):
        """
        Policy: "non-basic-economy reservation can be modified without changing the origin, destination, and trip type"
        Example: "change an economy classs round trip reservation from: JFK-LAX, LAX-JFK, to : JFK-TLV, TLV-JFK."
        """
        
        history = MagicMock()
        history.ask_bool.return_value = True

        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="sara_doe_496",
            origin="JFK",
            destination="TLV",
            flight_type="round_trip",
            cabin="economy",
            flights=[ReservationFlight(flight_number="HAT005", origin="JFK", destination="TLV", date="2024-05-01", price=800)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=800)],
            created_at=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None

        flights = [FlightInfo(flight_number="HAT005", date="2024-05-01")]

        guard_same_origin__destination_and_trip_type(history, api, "ZFA04Y", "economy", flights, "credit_card_7815826")

    def test_violation_change_origin_one_way_economy_reservation(self):
        """
        Policy: "non-basic-economy reservation can be modified without changing the origin, destination, and trip type"
        Example: "a one way trip economy reservation change to anothr flight from a different origin"
        """
        
        history = MagicMock()
        history.ask_bool.return_value = True

        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="sara_doe_496",
            origin="JFK",
            destination="LAX",
            flight_type="one_way",
            cabin="economy",
            flights=[ReservationFlight(flight_number="HAT006", origin="JFK", destination="LAX", date="2024-05-01", price=300)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=300)],
            created_at=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
            status=None
        )

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None

        flights = [FlightInfo(flight_number="HAT006", date="2024-05-01", origin="SFO")]

        with pytest.raises(PolicyViolationException):
            guard_same_origin__destination_and_trip_type(history, api, "ZFA04Y", "economy", flights, "credit_card_7815826")

    def test_violation_change_destination_one_way_business_reservation(self):
        """
        Policy: "non-basic-economy reservation can be modified without changing the origin, destination, and trip type"
        Example: "a one way trip business reservation change to anothr flight to a different destination"
        """
        
        history = MagicMock()
        history.ask_bool.return_value = True

        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="sara_doe_496",
            origin="JFK",
            destination="LAX",
            flight_type="one_way",
            cabin="business",
            flights=[ReservationFlight(flight_number="HAT007", origin="JFK", destination="LAX", date="2024-05-01", price=1000)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=1000)],
            created_at=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None

        flights = [FlightInfo(flight_number="HAT007", date="2024-05-01", destination="SFO")]

        with pytest.raises(PolicyViolationException):
            guard_same_origin__destination_and_trip_type(history, api, "ZFA04Y", "business", flights, "credit_card_7815826")

    def test_violation_change_trip_type_business_reservation(self):
        """
        Policy: "non-basic-economy reservation can be modified without changing the origin, destination, and trip type"
        Example: "change a business reservation with two flights, trip type from one way to round trip"
        """
        
        history = MagicMock()
        history.ask_bool.return_value = True

        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="sara_doe_496",
            origin="JFK",
            destination="LAX",
            flight_type="one_way",
            cabin="business",
            flights=[ReservationFlight(flight_number="HAT008", origin="JFK", destination="LAX", date="2024-05-01", price=1000)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=1000)],
            created_at=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None

        flights = [FlightInfo(flight_number="HAT008", date="2024-05-01")]

        with pytest.raises(PolicyViolationException):
            guard_same_origin__destination_and_trip_type(history, api, "ZFA04Y", "business", flights, "credit_card_7815826")

    def test_violation_change_origin_roundtrip_business_reservation(self):
        """
        Policy: "non-basic-economy reservation can be modified without changing the origin, destination, and trip type"
        Example: "change the orgin of a roundtrip business reservation"
        """
        
        history = MagicMock()
        history.ask_bool.return_value = True

        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="sara_doe_496",
            origin="JFK",
            destination="LAX",
            flight_type="round_trip",
            cabin="business",
            flights=[ReservationFlight(flight_number="HAT009", origin="JFK", destination="LAX", date="2024-05-01", price=2000)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=2000)],
            created_at=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None

        flights = [FlightInfo(flight_number="HAT009", date="2024-05-01", origin="SFO")]

        with pytest.raises(PolicyViolationException):
            guard_same_origin__destination_and_trip_type(history, api, "ZFA04Y", "business", flights, "credit_card_7815826")

    def test_violation_change_destination_roundtrip_business_reservation(self):
        """
        Policy: "non-basic-economy reservation can be modified without changing the origin, destination, and trip type"
        Example: "change the destination of a roundtrip business reservation"
        """
        
        history = MagicMock()
        history.ask_bool.return_value = True

        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="sara_doe_496",
            origin="JFK",
            destination="LAX",
            flight_type="round_trip",
            cabin="business",
            flights=[ReservationFlight(flight_number="HAT010", origin="JFK", destination="LAX", date="2024-05-01", price=2000)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=2000)],
            created_at=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None

        flights = [FlightInfo(flight_number="HAT010", date="2024-05-01", destination="SFO")]

        with pytest.raises(PolicyViolationException):
            guard_same_origin__destination_and_trip_type(history, api, "ZFA04Y", "business", flights, "credit_card_7815826")

    def test_violation_change_roundtrip_to_one_way_business_reservation(self):
        """
        Policy: "non-basic-economy reservation can be modified without changing the origin, destination, and trip type"
        Example: "change a roundtrip business reservation to a one way"
        """
        
        history = MagicMock()
        history.ask_bool.return_value = True

        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="sara_doe_496",
            origin="JFK",
            destination="LAX",
            flight_type="round_trip",
            cabin="business",
            flights=[ReservationFlight(flight_number="HAT011", origin="JFK", destination="LAX", date="2024-05-01", price=2000)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=2000)],
            created_at=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None

        flights = [FlightInfo(flight_number="HAT011", date="2024-05-01")]

        with pytest.raises(PolicyViolationException):
            guard_same_origin__destination_and_trip_type(history, api, "ZFA04Y", "business", flights, "credit_card_7815826")

    def test_violation_gold_user_updates_destination_business_class(self):
        """
        Policy: "non-basic-economy reservation can be modified without changing the origin, destination, and trip type"
        Example: "A gold user requests to updates destination to 'LAX' for their business class reservation."
        """
        
        history = MagicMock()
        history.ask_bool.return_value = True

        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="sara_doe_496",
            origin="JFK",
            destination="SFO",
            flight_type="round_trip",
            cabin="business",
            flights=[ReservationFlight(flight_number="HAT012", origin="JFK", destination="SFO", date="2024-05-01", price=2000)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=2000)],
            created_at=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None

        flights = [FlightInfo(flight_number="HAT012", date="2024-05-01", destination="LAX")]

        with pytest.raises(PolicyViolationException):
            guard_same_origin__destination_and_trip_type(history, api, "ZFA04Y", "business", flights, "credit_card_7815826")

    def test_violation_user_updates_trip_type_round_trip_to_one_way(self):
        """
        Policy: "non-basic-economy reservation can be modified without changing the origin, destination, and trip type"
        Example: "A user requests to update trip type from 'round-trip' to 'one-way' for their reservation."
        """
        
        history = MagicMock()
        history.ask_bool.return_value = True

        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="sara_doe_496",
            origin="JFK",
            destination="LAX",
            flight_type="round_trip",
            cabin="business",
            flights=[ReservationFlight(flight_number="HAT013", origin="JFK", destination="LAX", date="2024-05-01", price=2000)],
            passengers=[Passenger(first_name="John", last_name="Doe", dob="1990-01-01")],
            payment_history=[Payment(payment_id="credit_card_7815826", amount=2000)],
            created_at=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"),
            total_baggages=2,
            nonfree_baggages=1,
            insurance="yes",
            status=None
        )

        api = MagicMock(spec=I_Airline)
        api.get_reservation_details.side_effect = lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None

        flights = [FlightInfo(flight_number="HAT013", date="2024-05-01")]

        with pytest.raises(PolicyViolationException):
            guard_same_origin__destination_and_trip_type(history, api, "ZFA04Y", "business", flights, "credit_card_7815826")
