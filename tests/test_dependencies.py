import inspect
import logging
from pathlib import Path
import os
from dotenv import load_dotenv
import pytest
load_dotenv()

from toolguard.gen_py.tool_dependencies import tool_dependencies
from toolguard.data_types import ToolPolicyItem
from toolguard.gen_py.domain_from_funcs import generate_domain_from_functions
from tau2.domains.airline.tools import AirlineTools

current_dir = str(Path(__file__).parent)
from programmatic_ai.config import settings
settings.sdk = os.getenv("PROG_AI_PROVIDER") # type: ignore

book_reservation_signature = """
    def guard_book_reservation(api: I_Airline, user_id: str, origin: str, destination: str, flight_type: Literal['round_trip', 'one_way'], cabin: Literal['business', 'economy', 'basic_economy'], flights: List[FlightInfo], passengers: List[Passenger], payment_methods: List[Payment], total_baggages: int, nonfree_baggages: int, insurance: Literal['yes', 'no']):
    /"/"/"
    Checks that a tool call complies to the policies.

    Args:
        api (I_Airline): api to access other tools.
        user_id: The ID of the user to book the reservation such as 'sara_doe_496'`.
        origin: The IATA code for the origin city such as 'SFO'.
        destination: The IATA code for the destination city such as 'JFK'.
        flight_type: The type of flight such as 'one_way' or 'round_trip'.
        cabin: The cabin class such as 'basic_economy', 'economy', or 'business'.
        flights: An array of objects containing details about each piece of flight.
        passengers: An array of objects containing details about each passenger.
        payment_methods: An array of objects containing details about each payment method.
        total_baggages: The total number of baggage items to book the reservation.
        nonfree_baggages: The number of non-free baggage items to book the reservation.
        insurance: Whether the reservation has insurance. 
    /"/"/"
"""


update_flights_signature = """
    def guard_update_reservation_flights(api: I_Airline, reservation_id: str, cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo], payment_id: str) -> Reservation:
        /"/"/"
        Checks that a tool call complies to the policies.

        Args:
            api (I_Airline): api to access other tools.
            reservation_id: The reservation ID, such as 'ZFA04Y'.
            cabin: The cabin class of the reservation
            flights: An array of objects containing details about each piece of flight in the ENTIRE new reservation. Even if the a flight segment is not changed, it should still be included in the array.
            payment_id: The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'.
    /"/"/"    
"""

class TestToolsDependencies:

    @classmethod
    def setup_class(cls):
        funcs = [member for name, member in inspect.getmembers(AirlineTools, predicate=inspect.isfunction)
            if getattr(member, "__tool__", None)]  # only @is_tool]
        domain = generate_domain_from_functions("tests/temp", "airline", funcs, ["tau2"])

        cls.domain = domain.get_definitions_only()

    @classmethod
    def teardown_class(cls):
        """Run once after all tests."""
        print("Tearing down class resources")

    @pytest.mark.asyncio
    async def test_args_only(self):
        policy = ToolPolicyItem(
            name="up to five passengers",
            description="The total number of passengers in a reservation does not exceed five.",
            references=[],
            compliance_examples=[],
            violation_examples=[]
        )
        try:
            assert await tool_dependencies(policy, book_reservation_signature, self.domain) == set()
        except Exception as ex:
            logging.exception(ex)
            assert False

    @pytest.mark.asyncio
    async def test_payment_in_user(self):
        policy = ToolPolicyItem(
            name="payment method exists",
            description="""All payment methods used are already present in the user's profile. 
        Each reservation can use at most one travel certificate, one credit card, and three gift cards. """,
            references=[],
            compliance_examples=[],
            violation_examples=[]
        )
        assert await tool_dependencies(policy, book_reservation_signature, self.domain) == {"get_user_details"}

    @pytest.mark.asyncio
    async def test_payment_in_args(self):
        policy = ToolPolicyItem(
            name="payment methods limit",
            description="Each reservation can use at most one travel certificate, one credit card, and three gift cards.",
            references=[],
            compliance_examples=[],
            violation_examples=[]
        )
        deps = await tool_dependencies(policy, book_reservation_signature, self.domain)
        assert deps  == {"get_user_details"}

    @pytest.mark.asyncio
    async def test_membership(self):
        policy = ToolPolicyItem(
            name="max bags",
            description="""
        If the booking user is a regular member, 0 free checked bag for each basic economy passenger, 1 free checked bag for each economy passenger, and 2 free checked bags for each business passenger. 
        If the booking user is a silver member, 1 free checked bag for each basic economy passenger, 2 free checked bag for each economy passenger, and 3 free checked bags for each business passenger. 
        If the booking user is a gold member, 2 free checked bag for each basic economy passenger, 3 free checked bag for each economy passenger, and 3 free checked bags for each business passenger.
        """,
            references=[],
            compliance_examples=[],
            violation_examples=[]
        )
        assert await tool_dependencies(policy, book_reservation_signature, self.domain) == {"get_user_details"}

    @pytest.mark.asyncio
    async def test_flight_status(self):
        policy = ToolPolicyItem(
            name="flight status",
            description="""The agent must ensure that the flight status is 'available' before booking.
        Flights with status 'delayed', 'on time', or 'flying' cannot be booked.
        """,
            references=[],
            compliance_examples=[],
            violation_examples=[]
        )
        assert await tool_dependencies(policy, book_reservation_signature, self.domain) == {"get_flight_status"}
    
    @pytest.mark.asyncio
    async def test_update_flight_basic_economy(self):
        policy = ToolPolicyItem(
            name = "Basic Economy Flight Modification Restriction",
            description = "Basic economy flights cannot be modified. The agent must verify the reservation's cabin class before calling the flight update API.",
            references=[],
            compliance_examples=[],
            violation_examples=[]
        )
        assert await tool_dependencies(policy, update_flights_signature, self.domain) == {"get_reservation_details"}

    @pytest.mark.asyncio
    async def test_indirect_api(self):
        policy = ToolPolicyItem(
            name = "CannotUpdateOriginDestinationTripType",
            description = "When changing flights in a reservation, the agent must ensure that the origin, destination, and trip type remain unchanged.",
            references=[],
            compliance_examples=[],
            violation_examples=[]
        )
        deps = await tool_dependencies(policy, update_flights_signature, self.domain)
        assert deps == {"get_reservation_details", "get_scheduled_flight"}
