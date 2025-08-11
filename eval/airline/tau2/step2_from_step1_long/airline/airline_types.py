# Auto-generated type definitions
from enum import Enum
from abc import ABC
from typing import *
from pydantic import BaseModel, Field

class FlightBase(BaseModel):
    flight_number: str  # Unique flight identifier
    origin: str  # IATA code for origin airport
    destination: str  # IATA code for destination airport

class Address(BaseModel):
    address1: str  # Primary address line
    address2: Optional[str]  # Secondary address line (optional)
    city: str  # City name
    country: str  # Country name
    state: str  # State or province name
    zip: str  # Postal code

class FlightDateStatusAvailable(BaseModel):
    status: Literal['available']  # Indicates flight is available for booking
    available_seats: dict[Literal['business', 'economy', 'basic_economy'], int]  # Available seats by class
    prices: dict[Literal['business', 'economy', 'basic_economy'], int]  # Current prices by class

class FlightDateStatusCancelled(BaseModel):
    status: Literal['cancelled']  # Indicates flight was cancelled

class PaymentMethodBase(BaseModel):
    source: str  # Type of payment method
    id: str  # Unique identifier for the payment method

class FlightDateStatusLanded(BaseModel):
    status: Literal['landed']  # Indicates flight has landed
    actual_departure_time_est: str  # Actual departure time in EST in the format YYYY-MM-DDTHH:MM:SS, e.g 2024-05-15T06:04:00
    actual_arrival_time_est: str  # Actual arrival time in EST in the format YYYY-MM-DDTHH:MM:SS, e.g 2024-05-15T07:30:00

class FlightInfo(BaseModel):
    flight_number: str  # Flight number, such as 'HAT001'.
    date: str  # The date for the flight in the format 'YYYY-MM-DD', such as '2024-05-01'.

class FlightDataStatusFlying(BaseModel):
    status: Literal['flying']  # Indicates flight is in flight
    actual_departure_time_est: str  # Actual departure time in EST in the format YYYY-MM-DDTHH:MM:SS, e.g 2024-05-15T06:04:00
    estimated_arrival_time_est: str  # Estimated arrival time in EST in the format YYYY-MM-DDTHH:MM:SS, e.g 2024-05-15T07:30:00

class AirportCode(BaseModel):
    iata: str  # IATA code
    city: str  # City name

class FlightDataStatusOnTime(BaseModel):
    status: Literal['on time']  # Indicates flight is on time
    estimated_departure_time_est: str  # Estimated departure time in EST in the format YYYY-MM-DDTHH:MM:SS, e.g 2024-05-15T06:04:00
    estimated_arrival_time_est: str  # Estimated arrival time in EST in the format YYYY-MM-DDTHH:MM:SS, e.g 2024-05-15T07:30:00

class FlightDateStatusDelayed(BaseModel):
    status: Literal['delayed']  # Indicates flight was delayed
    estimated_departure_time_est: str  # Estimated departure time in EST in the format YYYY-MM-DDTHH:MM:SS, e.g 2024-05-15T06:04:00
    estimated_arrival_time_est: str  # Estimated arrival time in EST in the format YYYY-MM-DDTHH:MM:SS, e.g 2024-05-15T07:30:00

class Payment(BaseModel):
    payment_id: str  # Unique identifier for the payment
    amount: int  # Payment amount in dollars

class Passenger(BaseModel):
    first_name: str  # Passenger's first name
    last_name: str  # Passenger's last name
    dob: str  # Date of birth in YYYY-MM-DD format

class Name(BaseModel):
    first_name: str  # The person's first name
    last_name: str  # The person's last name

class DirectFlight(FlightBase):
    status: Literal['available']  # Indicates flight is available for booking
    scheduled_departure_time_est: str  # Scheduled departure time in EST in the format HH:MM:SS, e.g 06:00:00
    scheduled_arrival_time_est: str  # Scheduled arrival time in EST in the format HH:MM:SS, e.g 07:00:00
    date: Optional[str]  # Flight date in YYYY-MM-DD format
    available_seats: dict[Literal['business', 'economy', 'basic_economy'], int]  # Available seats by class
    prices: dict[Literal['business', 'economy', 'basic_economy'], int]  # Current prices by class

class ReservationFlight(FlightBase):
    date: str  # Flight date in YYYY-MM-DD format
    price: int  # Flight price in dollars.

class GiftCard(PaymentMethodBase):
    source: Literal['gift_card']  # Indicates this is a gift card payment method
    amount: float  # Gift card value amount
    id: str  # Unique identifier for the gift card

class CreditCard(PaymentMethodBase):
    source: Literal['credit_card']  # Indicates this is a credit card payment method
    brand: str  # Credit card brand (e.g., visa, mastercard)
    last_four: str  # Last four digits of the credit card

class Certificate(PaymentMethodBase):
    source: Literal['certificate']  # Indicates this is a certificate payment method
    amount: float  # Certificate value amount

class Flight(FlightBase):
    scheduled_departure_time_est: str  # Scheduled departure time in EST in the format HH:MM:SS, e.g 06:00:00
    scheduled_arrival_time_est: str  # Scheduled arrival time in EST in the format HH:MM:SS, e.g 07:00:00
    dates: dict[str, Union[FlightDateStatusAvailable, FlightDateStatusLanded, FlightDateStatusCancelled, FlightDateStatusDelayed, FlightDataStatusFlying, FlightDataStatusOnTime]]  # Flight status by date (YYYY-MM-DD)

class Reservation(BaseModel):
    reservation_id: str  # Unique identifier for the reservation
    user_id: str  # ID of the user who made the reservation
    origin: str  # IATA code for trip origin
    destination: str  # IATA code for trip destination
    flight_type: Literal['round_trip', 'one_way']  # Type of trip
    cabin: Literal['business', 'economy', 'basic_economy']  # Selected cabin class
    flights: list[ReservationFlight]  # List of flights in the reservation
    passengers: list[Passenger]  # List of passengers on the reservation
    payment_history: list[Payment]  # History of payments for this reservation
    created_at: str  # Timestamp when reservation was created in the format YYYY-MM-DDTHH:MM:SS
    total_baggages: int  # Total number of bags in reservation
    nonfree_baggages: int  # Number of paid bags in reservation
    insurance: Literal['yes', 'no']  # Whether travel insurance was purchased
    status: Optional[Literal['cancelled']]  # Status of the reservation

class User(BaseModel):
    user_id: str  # Unique identifier for the user
    name: Name  # User's full name
    address: Address  # User's address information
    email: str  # User's email address
    dob: str  # User's date of birth in the format YYYY-MM-DD, e.g 1990-04-05
    payment_methods: dict[str, Union[CreditCard, GiftCard, Certificate]]  # User's saved payment methods
    saved_passengers: list[Passenger]  # User's saved passenger information
    membership: Literal['gold', 'silver', 'regular']  # User's membership level
    reservations: list[str]  # List of user's reservation IDs
