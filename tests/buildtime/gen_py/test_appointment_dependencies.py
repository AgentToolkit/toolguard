import os
from pathlib import Path
import mellea
import pytest
from toolguard.buildtime.gen_py.mellea_simple import SimpleBackend
from toolguard.buildtime.gen_py.tool_dependencies import tool_dependencies
from toolguard.buildtime.gen_py.domain_from_openapi import generate_domain_from_openapi
from toolguard.buildtime.llm.tg_litellm import LitellmModel


@pytest.mark.asyncio
async def test_appointment_slot_fee_dependency():
    py_root = Path("tests/tmp")
    os.makedirs(py_root, exist_ok=True)
    domain = generate_domain_from_openapi(
        py_root, "appo", Path("tests/resources/appointments_oas.json")
    ).get_definitions_only()
    policy_txt = "Gold members receive a 10% discount on the slot visit fee."
    tool_signature = "schedule_appointment(self, args:ScheduleAppointmentArgs)"

    model = "o1-2024-12-17"  # "gpt-4o-2024-08-06"
    llm_provider = "azure"
    llm = LitellmModel(model, llm_provider)
    mellea_backend = SimpleBackend(llm)
    mellea_session = mellea.MelleaSession(mellea_backend)

    deps = await tool_dependencies(policy_txt, tool_signature, domain, mellea_session)

    assert len(deps) == 2
    assert "get_user" in deps
    assert "get_appointment_slot" in deps
