import inspect
import os
from pathlib import Path
import mellea
import pytest

from toolguard.buildtime.gen_py.tool_dependencies import tool_dependencies
from toolguard.buildtime.gen_py.domain_from_funcs import generate_domain_from_functions
from toolguard.buildtime.gen_py.mellea_simple import SimpleBackend
from toolguard.buildtime.llm.tg_litellm import LitellmModel
from tau2.domains.airline.tools import AirlineTools
from tau2.environment.toolkit import ToolType, is_tool
from tau2.domains.airline.data_model import FlightBase

current_dir = str(Path(__file__).parent)
# from programmatic_ai.config import settings
# settings.sdk = os.getenv("PROG_AI_PROVIDER") # type: ignore

book_reservation_signature = """
    guard_book_reservation(api: I_Airline, user_id: str, origin: str, destination: str, flight_type: Literal['round_trip', 'one_way'], cabin: Literal['business', 'economy', 'basic_economy'], flights: List[FlightInfo], passengers: List[Passenger], payment_methods: List[Payment], total_baggages: int, nonfree_baggages: int, insurance: Literal['yes', 'no'])
"""


update_flights_signature = """
    guard_update_reservation_flights(api: I_Airline, reservation_id: str, cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo], payment_id: str) -> Reservation
"""


# The Tau2 API is missing this method, which is required to check the last test: test_indirect_api()
class ExtendedAirline(AirlineTools):
    @is_tool(ToolType.READ)
    def get_scheduled_flight(self, flight_id: str) -> FlightBase:  # type: ignore
        """
        Returns details on a scheduled flights, such as origin and destination.
        """
        ...


class TestToolsDependencies:
    @classmethod
    def setup_class(cls):
        funcs = [
            member
            for name, member in inspect.getmembers(
                ExtendedAirline, predicate=inspect.isfunction
            )
            if getattr(member, "__tool__", None)
        ]  # only @is_tool]
        py_root = Path("tests/tmp")
        domain = generate_domain_from_functions(py_root, "airline", funcs, ["tau2"])

        cls.domain = domain.get_definitions_only()

    @classmethod
    def teardown_class(cls):
        """Run once after all tests."""
        print("Tearing down class resources")

    @pytest.fixture(autouse=True)
    def session(self):
        llm = LitellmModel(
            model_name=os.getenv("MODEL_NAME") or "Azure/gpt-5-2025-08-07",
            provider=os.getenv("LLM_PROVIDER") or "azure",
            kw_args={
                "api_base": os.getenv("LLM_API_BASE"),
                "api_version": os.getenv("LLM_API_VERSION"),
                "api_key": os.getenv("LLM_API_KEY"),
            },
        )
        mellea_backend = SimpleBackend(llm)
        return mellea.MelleaSession(mellea_backend)

    @pytest.mark.asyncio
    async def test_args_only(self, session):
        policy = "The total number of passengers in a reservation does not exceed five."
        assert (
            await tool_dependencies(
                policy, book_reservation_signature, self.domain, session
            )
            == set()
        )

    @pytest.mark.asyncio
    async def test_payment_in_user(self, session):
        policy = """All payment methods used are already present in the user's profile.
        Each reservation can use at most one travel certificate, one credit card, and three gift cards. """
        assert await tool_dependencies(
            policy, book_reservation_signature, self.domain, session
        ) == {"get_user_details"}

    @pytest.mark.asyncio
    async def test_payment_in_args(self, session):
        policy = "Each reservation can use at most one travel certificate, one credit card, and three gift cards."
        deps = await tool_dependencies(
            policy, book_reservation_signature, self.domain, session
        )
        assert deps == {"get_user_details"}

    @pytest.mark.asyncio
    async def test_membership(self, session):
        policy = """
        If the booking user is a regular member, 0 free checked bag for each basic economy passenger, 1 free checked bag for each economy passenger, and 2 free checked bags for each business passenger.
        If the booking user is a silver member, 1 free checked bag for each basic economy passenger, 2 free checked bag for each economy passenger, and 3 free checked bags for each business passenger.
        If the booking user is a gold member, 2 free checked bag for each basic economy passenger, 3 free checked bag for each economy passenger, and 3 free checked bags for each business passenger.
        """
        assert await tool_dependencies(
            policy, book_reservation_signature, self.domain, session
        ) == {"get_user_details"}

    @pytest.mark.asyncio
    async def test_flight_status(self, session):
        policy = """The agent must ensure that the flight status is 'available' before booking.
        Flights with status 'delayed', 'on time', or 'flying' cannot be booked.
        """
        assert await tool_dependencies(
            policy, book_reservation_signature, self.domain, session
        ) == {"get_flight_status"}

    @pytest.mark.asyncio
    async def test_update_flight_basic_economy(self, session):
        policy = "Basic economy flights cannot be modified. The agent must verify the reservation's cabin class before calling the flight update API."
        assert await tool_dependencies(
            policy, update_flights_signature, self.domain, session
        ) == {"get_reservation_details"}

    # This test succeeds only with §§advanced models (eg, o1. but not gpt-4o)
    @pytest.mark.asyncio
    async def test_indirect_api(self, session):
        policy = "When changing flights in a reservation, the agent must ensure that the origin, destination, and trip type remain unchanged."
        deps = await tool_dependencies(
            policy, update_flights_signature, self.domain, session
        )
        assert deps == {"get_reservation_details", "get_scheduled_flight"}
