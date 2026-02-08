from datetime import datetime, timedelta
import os
import shutil
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from tau2.domains.airline.data_model import (
    Passenger,
    Reservation,
    ReservationFlight,
    Payment,
)
from tau2.domains.airline.tools import AirlineTools

from toolguard.buildtime import I_TG_LLM, generate_guard_specs, generate_guards_code
from toolguard.buildtime.llm.tg_litellm import LitellmModel
from toolguard.extra import api_cls_to_functions
from toolguard.runtime import load_toolguards
from toolguard.runtime.data_types import PolicyViolationException
from toolguard.runtime.tool_invokers.methods import ToolMethodsInvoker

model = os.getenv("MODEL_NAME") or "gpt-4o-2024-08-06"
llm_provider = "azure"
app_name = "calc"  # dont use "calculator", as it conflicts with example name
STEP1 = "step1"
STEP2 = "step2"


def llm() -> I_TG_LLM:
    return LitellmModel(
        model_name=model,
        provider=os.getenv("LLM_PROVIDER") or "azure",
        kw_args={
            "api_base": os.getenv("LLM_API_BASE"),
            "api_version": os.getenv("LLM_API_VERSION"),
            "api_key": os.getenv("LLM_API_KEY"),
        },
    )


@pytest.mark.asyncio
async def test_tau2_simple():
    work_dir = Path("tests/tmp/e2e/tau2_airline_simple")
    fns = api_cls_to_functions(AirlineTools)
    tool_fns = [fn for fn in fns if hasattr(fn, "__tool__")]

    run_dir = work_dir / model
    shutil.rmtree(run_dir, ignore_errors=True)
    run_dir.mkdir(parents=True, exist_ok=True)
    step1_out_dir = run_dir / STEP1
    step2_out_dir = run_dir / STEP2

    policy_text = "Users cannot book a flight for more than 5 passengers"

    specs = await generate_guard_specs(
        policy_text=policy_text,
        tools=tool_fns,
        work_dir=step1_out_dir,
        llm=llm(),
        short=True,
    )
    assert len(specs) == len(tool_fns)

    book_spec = next(spec for spec in specs if spec.tool_name == "book_reservation")
    assert len(book_spec.policy_items) == 1
    item0 = book_spec.policy_items[0]
    assert len(item0.compliance_examples) > 1
    assert len(item0.violation_examples) > 1

    update_spec = next(
        spec for spec in specs if spec.tool_name == "update_reservation_passengers"
    )
    assert len(update_spec.policy_items) == 1
    item0 = update_spec.policy_items[0]
    assert len(item0.compliance_examples) > 1
    assert len(item0.violation_examples) > 1

    other_specs = [spec for spec in specs if spec not in [book_spec, update_spec]]
    assert all([not spec.policy_items for spec in other_specs])

    # spec = ToolGuardSpec.load("/Users/davidboaz/Documents/GitHub/toolguard/tests/tmp/e2e/calculator/tool_functions_short/GCP/claude-4-sonnet/step1/divide_tool.json")
    # specs = [spec]
    await generate_guards_code(
        tool_specs=specs,
        tools=tool_fns,
        work_dir=step2_out_dir,
        llm=llm(),
        app_name="tau2_simple",
    )

    # Runtime
    api = MagicMock()
    with load_toolguards(step2_out_dir) as toolguard:
        # test compliance
        await toolguard.guard_toolcall(
            "book_reservation",
            {
                "passengers": 5
                * [Passenger(first_name="John", last_name="Doe", dob="1990-01-01")]
            },
            ToolMethodsInvoker(api),
        )
        await toolguard.guard_toolcall(
            "update_reservation_passengers",
            {
                "passengers": 5
                * [Passenger(first_name="John", last_name="Doe", dob="1990-01-01")]
            },
            ToolMethodsInvoker(api),
        )
        with unittest.TestCase().assertRaises(PolicyViolationException):
            await toolguard.guard_toolcall(
                "book_reservation",
                {
                    "passengers": 6
                    * [Passenger(first_name="John", last_name="Doe", dob="1990-01-01")]
                },
                ToolMethodsInvoker(api),
            )
        with unittest.TestCase().assertRaises(PolicyViolationException):
            await toolguard.guard_toolcall(
                "update_reservation_passengers",
                {
                    "passengers": 6
                    * [Passenger(first_name="John", last_name="Doe", dob="1990-01-01")]
                },
                ToolMethodsInvoker(api),
            )


@pytest.mark.asyncio
async def test_tau2_complex_api():
    work_dir = Path("tests/tmp/e2e/tau2_complex_api")
    fns = api_cls_to_functions(AirlineTools)
    tool_fns = [fn for fn in fns if hasattr(fn, "__tool__")]

    run_dir = work_dir / model
    shutil.rmtree(run_dir, ignore_errors=True)
    run_dir.mkdir(parents=True, exist_ok=True)
    step1_out_dir = run_dir / STEP1
    step2_out_dir = run_dir / STEP2

    policy_text = """To use the 'cancel_reservation' tool, at least one the following must hold:
    1) The cancellation is within 24 hours of booking,
    2) The airline cancelled the flight,
    3) For economy class, cancellation is only allowed if travel insurance was purchased and qualifies,
    4) Business class flights can be cancelled anytime.
    These conditions must be validated prior to invoking the tool.
    """

    specs = await generate_guard_specs(
        policy_text=policy_text,
        tools=tool_fns,
        work_dir=step1_out_dir,
        llm=llm(),
        short=True,
    )
    assert len(specs) == len(tool_fns)

    cancel_spec = next(spec for spec in specs if spec.tool_name == "cancel_reservation")
    assert len(cancel_spec.policy_items) == 1
    item0 = cancel_spec.policy_items[0]
    assert len(item0.compliance_examples) > 1
    assert len(item0.violation_examples) > 1

    other_specs = [spec for spec in specs if spec not in [cancel_spec]]
    assert all([not spec.policy_items for spec in other_specs])

    # spec = ToolGuardSpec.load("/Users/davidboaz/Documents/GitHub/toolguard/tests/tmp/e2e/calculator/tool_functions_short/GCP/claude-4-sonnet/step1/divide_tool.json")
    # specs = [spec]
    await generate_guards_code(
        tool_specs=specs,
        tools=tool_fns,
        work_dir=step2_out_dir,
        llm=llm(),
        app_name="tau2_api",
    )

    # Positive Example
    api = MagicMock()
    with load_toolguards(step2_out_dir) as toolguard:
        from tau2_api.i_tau2_api import ITau2Api

        created_at = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%S")
        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="sara_doe_496",
            origin="SFO",
            destination="JFK",
            flight_type="round_trip",
            cabin="business",
            flights=[
                ReservationFlight(
                    flight_number="HAT001",
                    origin="SFO",
                    destination="JFK",
                    date="2024-06-15",
                    price=1200,
                )
            ],
            passengers=[
                Passenger(first_name="John", last_name="Doe", dob="1990-01-01")
            ],
            payment_history=[Payment(payment_id="pay_001", amount=1200)],
            created_at=created_at,
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
        )

        api.get_reservation_details = AsyncMock()
        api.get_reservation_details.side_effect = (
            lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None
        )
        api.get_flight_status = AsyncMock()
        api.get_flight_status.side_effect = (
            lambda flight_number, date: "scheduled"
            if flight_number == "HAT001"
            else None
        )

        # Should not raise exception - business class can be cancelled anytime
        await toolguard.guard_toolcall(
            "cancel_reservation",
            args={"reservation_id": "ZFA04Y"},
            delegate=ToolMethodsInvoker(api),
        )

    # Negative Example
    with load_toolguards(step2_out_dir) as toolguard:
        from tau2_api.i_tau2_api import ITau2Api

        created_at = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%S")
        reservation = Reservation(
            reservation_id="ZFA04Y",
            user_id="sara_doe_496",
            origin="SFO",
            destination="JFK",
            flight_type="round_trip",
            cabin="basic_economy",
            flights=[
                ReservationFlight(
                    flight_number="HAT001",
                    origin="SFO",
                    destination="JFK",
                    date="2024-06-15",
                    price=1200,
                )
            ],
            passengers=[
                Passenger(first_name="John", last_name="Doe", dob="1990-01-01")
            ],
            payment_history=[Payment(payment_id="pay_001", amount=1200)],
            created_at=created_at,
            total_baggages=1,
            nonfree_baggages=0,
            insurance="no",
        )

        api: ITau2Api = MagicMock()

        async def get_reservation_side_effect(reservation_id: str):
            return reservation if reservation_id == "ZFA04Y" else None

        api.get_reservation_details = AsyncMock(side_effect=get_reservation_side_effect)
        api.get_flight_status = AsyncMock()
        api.get_flight_status.side_effect = (
            lambda flight_number, date: "scheduled"
            if flight_number == "HAT001"
            else None
        )

        try:
            await toolguard.guard_toolcall(
                "cancel_reservation",
                args={"reservation_id": "ZFA04Y"},
                delegate=ToolMethodsInvoker(api),
            )
            assert False
        except PolicyViolationException as ex:
            assert ex.message
            assert len(ex.rule) == 2
            assert ex.rule[0] == "cancel_reservation"
