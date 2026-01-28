import os
from pathlib import Path
import shutil
import unittest
from unittest.mock import MagicMock
import pytest
from tau2.domains.airline.data_model import Passenger
from toolguard.buildtime import I_TG_LLM, generate_guard_specs, generate_guards_code
from toolguard.buildtime.llm.tg_litellm import LitellmModel
from toolguard.extra import api_cls_to_functions
from toolguard.runtime import load_toolguards
from toolguard.runtime.data_types import PolicyViolationException
from toolguard.runtime.tool_invokers.methods import ToolMethodsInvoker
from tau2.domains.airline.tools import AirlineTools

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
    work_dir = Path("tests/tmp/e2e/tau2_airline")
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
