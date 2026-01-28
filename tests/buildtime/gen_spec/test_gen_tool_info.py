from pathlib import Path

from toolguard.buildtime.gen_spec.fn_to_toolinfo import function_to_toolInfo
from toolguard.buildtime.gen_spec.oas_to_toolinfo import openapi_to_toolinfos
from toolguard.buildtime.utils.open_api import OpenAPI


def test_oas_appointment_tool_info():
    oas_path = Path("tests/examples/appointments/appointments_oas.json")
    oas = OpenAPI.load_from(oas_path)

    infos = openapi_to_toolinfos(oas)
    info_by_name = {info.name: info for info in infos}
    assert len(info_by_name) == 12

    add_payment = info_by_name["add_payment_method"]
    params = ["user_id", "card_last_4", "card_brand", "card_exp", "card_id"]
    assert all([f in add_payment.parameters for f in params])
    assert add_payment.name == "add_payment_method"
    assert add_payment.summary.startswith("Adds a new payment method")
    assert add_payment.description.startswith("Adds a new payment method")
    assert (
        add_payment.signature
        == "add_payment_method(user_id: int, card_last_4: int, card_brand: str, card_exp: str, card_id: str) -> int"
    )
    assert len(add_payment.parameters) == 5
    user_id = add_payment.parameters["user_id"]
    assert user_id.type == "int"
    assert (
        user_id.description
        == "The ID of the user to whom the payment method will be added."
    )
    assert user_id.required


def test_fn_to_toolinfo():
    def add_tool(a: float, b: float) -> float:
        """Adds two numbers.

        Args:
            a (float): The first number.
            b (float): The second number.

        Returns:
            float: The sum of a and b.
        """
        return a + b

    info = function_to_toolInfo(add_tool)

    assert info.name == "add_tool"
    assert info.summary == "Adds two numbers."
    assert info.description.startswith("Adds two numbers.")
    assert info.signature == "add_tool(a: float, b: float) -> float"

    assert len(info.parameters) == 2
    param_a = info.parameters["a"]
    assert param_a.type == "float"
    assert param_a.description == "The first number."
    assert param_a.required

    param_b = info.parameters["b"]
    assert param_b.type == "float"
    assert param_b.description == "The second number."
    assert param_b.required
