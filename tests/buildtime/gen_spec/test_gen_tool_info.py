from pathlib import Path

from toolguard.buildtime.utils.open_api import OpenAPI
from toolguard.buildtime.oas_to_toolinfo import openapi_to_toolinfos


def test_gen_appointment_tool_info():
    oas_path = Path("tests/resources/appointments_oas.json")
    oas = OpenAPI.load_from(oas_path)

    infos = openapi_to_toolinfos(oas)

    assert len(infos) == 12
