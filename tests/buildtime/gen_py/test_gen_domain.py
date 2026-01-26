import importlib
import inspect
from pathlib import Path
import re
import sys
from typing import Dict

import pytest
from toolguard.buildtime.gen_py.domain_from_funcs import generate_domain_from_functions
from toolguard.buildtime.utils import py
from toolguard.buildtime.gen_py.domain_from_openapi import generate_domain_from_openapi
from toolguard.buildtime.utils import pyright
from tau2.domains.airline.tools import AirlineTools
from toolguard.buildtime.utils.open_api import OpenAPI


def load_class(
    project_root: Path,
    module_name: str,
    class_name: str,
):
    sys.path.insert(0, str(project_root))
    try:
        module = importlib.import_module(module_name)
        return getattr(module, class_name)
    finally:
        sys.path.pop(0)


@pytest.mark.asyncio
async def test_generate_domain_from_appointment_oas():
    oas_path = Path("tests/examples/appointments/appointments_oas.json")
    oas = OpenAPI.load_from(oas_path)
    trg_path = Path("tests/tmp/appointments")
    pyright.config(trg_path)

    domain = generate_domain_from_openapi(py_path=trg_path, app_name="My-ApP", oas=oas)

    report = await pyright.run(trg_path, domain.app_api.file_name)
    assert report.summary.errorCount == 0  # no syntax errors

    api = load_class(
        trg_path,
        py.path_to_module(domain.app_api.file_name),
        domain.app_api_class_name,
    )

    expected_signatures = {
        "get_user_id": "(self, app:str, args:my_app.my_app_types.GetUserIdArgs)->int",
        "add_payment_method": "(self, args:my_app.my_app_types.AddPaymentMethodArgs)->int",
        "get_user": "(self, args:my_app.my_app_types.GetUserArgs)->my_app.my_app_types.GetUserResponse",
        "remove_appointment": "(self, args:my_app.my_app_types.RemoveAppointmentArgs)->Any",
    }
    assert_method_signature(api, expected_signatures)


def normalize_signature(sig: str) -> str:
    # Remove module prefixes like a.b.c.Type -> Type
    return re.sub(r"\b(?:\w+\.)+(\w+)", r"\1", sig.replace(" ", ""))


def assert_method_signature(actual_api, expected_signatures: Dict[str, str]):
    for method_name, expected in expected_signatures.items():
        method = getattr(actual_api, method_name)
        signature = str(inspect.signature(method)).replace(" ", "")
        assert normalize_signature(signature) == normalize_signature(expected), (
            f"{method_name}: {signature} != {expected}"
        )


@pytest.mark.asyncio
async def test_generate_domain_from_calculator_oas():
    oas_path = Path("tests/examples/calculator/inputs/oas.json")
    oas = OpenAPI.load_from(oas_path)
    trg_path = Path("tests/tmp/calc")
    pyright.config(trg_path)

    domain = generate_domain_from_openapi(py_path=trg_path, app_name="calc", oas=oas)

    report = await pyright.run(trg_path, domain.app_api.file_name)
    assert report.summary.errorCount == 0  # no syntax errors

    api = load_class(
        trg_path,
        py.path_to_module(domain.app_api.file_name),
        domain.app_api_class_name,
    )

    expected_signatures = {
        "add_tool": "(self, args:calc.calc_types.AddToolRequest)->float",
        "map_kdi_number": "(self, args:calc.calc_types.MapKdiNumberRequest)->float",
    }
    assert_method_signature(api, expected_signatures)


@pytest.mark.asyncio
async def test_generate_domain_from_tau2_functions():
    trg_path = Path("tests/tmp/tau2_airline")
    pyright.config(trg_path)

    funcs = [
        member
        for name, member in inspect.getmembers(
            AirlineTools, predicate=inspect.isfunction
        )
        if getattr(member, "__tool__", None)
    ]  # only @is_tool]

    domain = generate_domain_from_functions(
        py_path=trg_path, app_name="airline", funcs=funcs, include_module_roots=["tau2"]
    )

    report = await pyright.run(trg_path, domain.app_api.file_name)
    assert report.summary.errorCount == 0  # no syntax errors

    api = load_class(
        trg_path,
        py.path_to_module(domain.app_api.file_name),
        domain.app_api_class_name,
    )

    expected_signatures = {
        "book_reservation": "(self, user_id: str, origin: str, destination: str, flight_type: Literal['round_trip', 'one_way'], cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo| dict], passengers: list[Passenger| dict], payment_methods: list[Payment| dict], total_baggages: int, nonfree_baggages: int, insurance: Literal['yes', 'no']) -> Reservation",
        "list_all_airports": "(self) -> list[AirportCode]",
    }
    assert_method_signature(api, expected_signatures)
