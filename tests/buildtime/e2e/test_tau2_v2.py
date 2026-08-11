"""tau2 airline, generated through v2 specs instead of v1.

The v2 counterpart of `test_tau2.py`. This is the only e2e over a realistic
domain — 40-odd airline tools rather than five calculator functions — so it is
where v2's per-tool binding has to hold up: a one-sentence policy must attach to
the two tools it governs and to no others.

The `complex_api` case is the more interesting one for v2: the cancellation rule
cannot be decided from arguments alone, so v2 should declare a `tool_history`
requirement (a `get_reservation_details` lookup) and still be codegen-able,
because generated guards do get an `api` handle.

Needs LLM credentials and the tau2 package; skipped without either.
"""

import os
import shutil
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from dotenv import load_dotenv

from toolguard.buildtime import (
    I_TG_LLM,
    SpecV2Options,
    generate_guard_specs_v2_full,
    generate_guards_code,
    specs_v2_to_v1,
)
from toolguard.buildtime.llm.tg_litellm import LitellmModel
from toolguard.extra import api_cls_to_functions
from toolguard.runtime import load_toolguards
from toolguard.runtime.data_types import PolicyViolationException
from toolguard.runtime.tool_invokers.methods import ToolMethodsInvoker

load_dotenv()

tau2 = pytest.importorskip("tau2", reason="needs the tau2 package")
from tau2.domains.airline.data_model import (  # noqa: E402
    CabinClass,
    Insurance,
    Passenger,
    Payment,
    Reservation,
    ReservationFlight,
)
from tau2.domains.airline.tools import AirlineTools  # noqa: E402

WORK_ROOT = Path("tests/tmp/e2e/gen_spec_v2_tau2")

requires_llm = pytest.mark.skipif(
    not os.getenv("LLM_API_KEY"),
    reason="needs LLM credentials (LLM_API_KEY)",
)

# review_votes stays at the default 5 here, unlike the calculator e2e: with 40-odd
# airline tools there are many chances to bind a rule to a tool it does not govern,
# and the relevance vote is what has to reject those.
#
# on_tool_error="raise" so a model failure for one tool surfaces as that error rather
# than as a confusing "13 specs for 14 tools" count mismatch downstream. With 40-odd
# tools a transient unparseable-JSON response is not rare, and it must not be
# mistaken for a policy-binding defect.
FAST = SpecV2Options(
    add_iterations=1, review_votes=5, example_number=2, on_tool_error="raise"
)


def llm() -> I_TG_LLM:
    return LitellmModel(
        model_name=os.getenv("MODEL_NAME") or "gpt-4o-2024-08-06",
        provider=os.getenv("LLM_PROVIDER") or "azure",
        kw_args={
            "api_base": os.getenv("LLM_API_BASE"),
            "api_version": os.getenv("LLM_API_VERSION"),
            "api_key": os.getenv("LLM_API_KEY"),
        },
    )


def _airline_tools():
    fns = api_cls_to_functions(AirlineTools)
    return [fn for fn in fns if hasattr(fn, "__tool__")]


def _passengers(n: int):
    return n * [Passenger(first_name="John", last_name="Doe", dob="1990-01-01")]


async def _build(variant: str, policy_text: str, app_name: str, tool_fns):
    work_dir = WORK_ROOT / variant
    shutil.rmtree(work_dir, ignore_errors=True)

    specs = await generate_guard_specs_v2_full(
        policy_text,
        tool_fns,
        llm(),
        work_dir / "specs_v2",
        source_doc="inline policy",
        options=FAST,
    )

    assert len(specs) == len(tool_fns), "one spec per tool, empty ones included"

    v1_specs = specs_v2_to_v1(specs, known_tools=[fn.__name__ for fn in tool_fns])
    guards = await generate_guards_code(
        tool_specs=v1_specs,
        tools=tool_fns,
        work_dir=work_dir / "code",
        llm=llm(),
        app_name=app_name,
    )
    return specs, v1_specs, guards


def _spec_for(specs, tool_name):
    return next(spec for spec in specs if spec.tool_name == tool_name)


@requires_llm
async def test_tau2_simple():
    tool_fns = _airline_tools()
    policy_text = "Users cannot book a flight for more than 5 passengers"

    specs, v1_specs, guards = await _build(
        "simple", policy_text, "tau2_v2_simple", tool_fns
    )

    governed = ("book_reservation", "update_reservation_passengers")
    for name in governed:
        spec = _spec_for(specs, name)
        assert len(spec.policy_items) >= 1, f"{name} must be governed by the policy"
        item = spec.policy_items[0]
        assert item.compliance_examples and item.violation_examples
        assert item.trigger == "pre_tool"

    # The policy names one condition on one argument, so it must not spread to
    # tools it does not govern.
    for spec in specs:
        if spec.tool_name not in governed:
            assert not spec.policy_items, f"{spec.tool_name} should be ungoverned"

    # A passenger-count rule needs nothing but the arguments, so it must survive
    # the adapter — otherwise no guard is generated at all.
    for name in governed:
        v1_spec = _spec_for(v1_specs, name)
        assert any(not item.skip for item in v1_spec.policy_items), (
            f"{name}'s rule is argument-only and must be codegen-able"
        )

    api = MagicMock()
    with load_toolguards(guards.out_dir) as toolguard:
        for name in governed:
            await toolguard.guard_toolcall(
                name, {"passengers": _passengers(5)}, ToolMethodsInvoker(api)
            )
        for name in governed:
            with unittest.TestCase().assertRaises(PolicyViolationException):
                await toolguard.guard_toolcall(
                    name, {"passengers": _passengers(6)}, ToolMethodsInvoker(api)
                )


def _reservation(
    cabin: CabinClass, insurance: Insurance, days_ago: int = 14
) -> Reservation:
    created_at = (datetime.now() - timedelta(days=days_ago)).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    return Reservation(
        reservation_id="ZFA04Y",
        user_id="sara_doe_496",
        origin="SFO",
        destination="JFK",
        flight_type="round_trip",
        cabin=cabin,
        flights=[
            ReservationFlight(
                flight_number="HAT001",
                origin="SFO",
                destination="JFK",
                date="2024-06-15",
                price=1200,
            )
        ],
        passengers=_passengers(1),
        payment_history=[Payment(payment_id="pay_001", amount=1200)],
        created_at=created_at,
        total_baggages=1,
        nonfree_baggages=0,
        insurance=insurance,
    )


def _api_for(reservation: Reservation) -> MagicMock:
    api = MagicMock()
    api.get_reservation_details = AsyncMock()
    api.get_reservation_details.side_effect = (
        lambda reservation_id: reservation if reservation_id == "ZFA04Y" else None
    )
    api.get_flight_status = AsyncMock()
    api.get_flight_status.side_effect = (
        lambda flight_number, date: "scheduled" if flight_number == "HAT001" else None
    )
    return api


@requires_llm
async def test_tau2_complex_api():
    tool_fns = _airline_tools()
    policy_text = """To use the 'cancel_reservation' tool, at least one the following must hold:
    1) The cancellation is within 24 hours of booking,
    2) The airline cancelled the flight,
    3) For economy class, cancellation is only allowed if travel insurance was purchased and qualifies,
    4) Business class flights can be cancelled anytime.
    These conditions must be validated prior to invoking the tool.
    """

    specs, v1_specs, guards = await _build(
        "complex_api", policy_text, "tau2_v2_api", tool_fns
    )

    cancel_spec = _spec_for(specs, "cancel_reservation")
    assert len(cancel_spec.policy_items) >= 1
    item = cancel_spec.policy_items[0]
    assert item.compliance_examples and item.violation_examples
    # "validated prior to invoking the tool" is explicit in the policy.
    assert item.trigger == "pre_tool"
    # The cabin, booking time and insurance all live on the reservation, not in
    # the arguments, so the rule has to declare the lookup it depends on.
    assert item.requires.tool_history, (
        "cancellation depends on the reservation, so a tool lookup must be declared"
    )

    for spec in specs:
        if spec.tool_name != "cancel_reservation":
            assert not spec.policy_items, f"{spec.tool_name} should be ungoverned"

    assert any(
        not item.skip for item in _spec_for(v1_specs, "cancel_reservation").policy_items
    ), "a tool_history-only rule must remain codegen-able"

    # Business class can be cancelled anytime.
    with load_toolguards(guards.out_dir) as toolguard:
        await toolguard.guard_toolcall(
            "cancel_reservation",
            args={"reservation_id": "ZFA04Y"},
            delegate=ToolMethodsInvoker(_api_for(_reservation("business", "no"))),
        )

    # Basic economy without insurance, booked two weeks ago: none of the four
    # conditions hold.
    with load_toolguards(guards.out_dir) as toolguard:
        with unittest.TestCase().assertRaises(PolicyViolationException):
            await toolguard.guard_toolcall(
                "cancel_reservation",
                args={"reservation_id": "ZFA04Y"},
                delegate=ToolMethodsInvoker(
                    _api_for(_reservation("basic_economy", "no"))
                ),
            )
