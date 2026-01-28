import os
from pathlib import Path

import mellea
import pytest

from toolguard.buildtime.gen_py.domain_from_openapi import generate_domain_from_openapi
from toolguard.buildtime.gen_py.mellea_simple import SimpleBackend
from toolguard.buildtime.gen_py.tool_dependencies import tool_dependencies
from toolguard.buildtime.llm.i_tg_llm import I_TG_LLM
from toolguard.buildtime.llm.tg_litellm import LitellmModel
from toolguard.buildtime.utils.open_api import OpenAPI


@pytest.fixture
def litellm_llm() -> I_TG_LLM:
    return LitellmModel(
        model_name=os.getenv("MODEL_NAME") or "gpt-4o-2024-08-06",
        provider=os.getenv("LLM_PROVIDER") or "azure",
        kw_args={
            "api_base": os.getenv("LLM_API_BASE"),
            "api_version": os.getenv("LLM_API_VERSION"),
            "api_key": os.getenv("LLM_API_KEY"),
        },
    )


@pytest.mark.asyncio
async def test_appointment_slot_fee_dependency(litellm_llm: I_TG_LLM):
    py_root = Path("tests/tmp")
    os.makedirs(py_root, exist_ok=True)
    oas = OpenAPI.load_from(Path("tests/examples/appointments/appointments_oas.json"))
    domain = (
        await generate_domain_from_openapi(py_root, "appo", oas)
    ).get_definitions_only()
    policy_txt = "Gold members receive a 10% discount on the slot visit fee."
    tool_signature = "schedule_appointment(self, args:ScheduleAppointmentArgs)"

    mellea_backend = SimpleBackend(litellm_llm)
    mellea_session = mellea.MelleaSession(mellea_backend)

    deps = await tool_dependencies(policy_txt, tool_signature, domain, mellea_session)

    assert len(deps) == 2
    assert "get_user" in deps
    assert "get_appointment_slot" in deps
