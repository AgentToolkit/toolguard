import importlib
import inspect
from pathlib import Path
import sys
from toolguard.common import py
from toolguard.gen_py.domain_from_openapi import generate_domain_from_openapi
from toolguard.gen_py.utils import pyright


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


def test_generate_domain_from_appointment_oas():
    oas_path = Path("tests/appointments_oas.json")
    trg_path = Path("tests/tmp")
    pyright.config(trg_path)

    domain = generate_domain_from_openapi(
        py_path=trg_path, app_name="bla", openapi_file=oas_path
    )

    report = pyright.run(trg_path, domain.app_api.file_name)
    assert report.summary.errorCount == 0  # no syntax errors

    api = load_class(
        trg_path,
        py.path_to_module(domain.app_api.file_name),
        domain.app_api_class_name,
    )

    expected_signatures = {
        "get_user_id": "(self, app:str, args:bla.bla_types.GetUserIdArgs)->int",
        "add_payment_method": "(self, args:bla.bla_types.AddPaymentMethodArgs)->int",
        "get_user": "(self, args:bla.bla_types.GetUserArgs)->bla.bla_types.GetUserResponse",
        "remove_appointment": "(self, args:bla.bla_types.RemoveAppointmentArgs)->Any",
    }

    for method_name, expected in expected_signatures.items():
        method = getattr(api, method_name)
        signature = str(inspect.signature(method)).replace(" ", "")
        assert signature == expected.replace(" ", ""), (
            f"{method_name}: {signature} != {expected}"
        )
