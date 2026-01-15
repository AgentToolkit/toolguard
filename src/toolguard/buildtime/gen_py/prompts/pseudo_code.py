# mypy: ignore-errors


from toolguard.runtime.data_types import FileTwin
from mellea import generative


@generative
def tool_policy_pseudo_code(
    policy_txt: str, fn_to_analyze: str, data_types: FileTwin, api: FileTwin
) -> str:
    """
        Returns a pseudo code to check business constraints on a tool cool using an API

        Args:
            policy_txt (str): Business policy, in natural language, specifying a constraint on a process involving the tool under analysis.
            fn_to_analyze (str): The function signature of the tool under analysis.
            domain (Domain): Python code defining available data types and APIs for invoking other tools.

        Returns:
            str: A pseudo code descibing how to use the API function to validate that the tool call complies with the policy.

        * Available API functions are listed in `domain.app_api.content`. Data types are defined in `domain.app_types.content`.
        * You cannot assume other API functions.
        * For parameters and returned value data objects, you can access only the declared fields. Otherwise a syntax error occur.
            * Do not assume the presence of any additional fields.
            * Do not assume any implicit logic or relationships between field values (e.g., naming conventions).
        * List all the required API calls to check the business policy.
        * If some information is missing, you should call another api function passing a reference to the missing information.

        Examples:
    ```python
        domain = {
            "app_types": {
                "file_name": "car_types.py",
                "content": '''
                    class CarType(Enum):
                        SEDAN = "sedan"
                        SUV = "suv"
                        VAN = "van"
                    class Car:
                        plate_num: str
                        car_type: CarType
                    class PaymentMethod:
                        id: str
                    class Cash(PaymentMethod):
                        pass
                    class CreditCard(PaymentMethod):
                        active: bool
                    class Person:
                        id: str
                        driving_licence: str
                        payment_methods: Dict[str, PaymentMethod]
                    class Insurance:
                        doc_id: str
                        valid: bool
                    class CarOwnership:
                        owenr_id: str
                        start_date: str
                        end_date: str
                    class Payment:
                        payment_method_id: str
                        amount: float
                '''
            },
            "app_api": {
                "file_name": "cars_api.py",
                "content": '''
                    class CarAPI(ABC):
                        def buy_car(self, plate_num: str, owner_id: str, insurance_id: str, payments: List[Payment]): pass
                        def get_person(self, id: str) -> Person: pass
                        def get_insurance(self, id: str) -> Insurance: pass
                        def get_car(self, plate_num: str) -> Car: pass
                        def car_ownership_history(self, plate_num: str) -> List[CarOwnership]: pass
                        def delete_car(self, plate_num: str): pass
                        def list_all_cars_owned_by(self, id: str) -> List[Car]: pass
                        def are_relatives(self, person1_id: str, person2_id: str) -> bool: pass
                '''
            }
        }
    ```
    * Example 1: Look for information by reference
    ```
        tool_policy_pseudo_code(
            policy_txt = "when buying a car, check that the car owner has a driving licence and that the insurance is valid.",
            fn_to_analyze = "buy_car(plate_num: str, owner_id: str, insurance_id: str, payments: List[Payment])",
            domain = domain
        )
    ```
    may return:
    ```
        user = api.get_person(owner_id)
        assert user.driving_licence
        insurance = api.get_insurance(insurance_id)
        assert insurance.valid
    ```

    * Example 2: No relevant tool in the API
    ```
        tool_policy_pseudo_code(
            policy_txt = "when buying a car, check that it is not a holiday today",
            fn_to_analyze = "buy_car(plate_num: str, owner_id: str, insurance_id: str, payments: List[Payment])",
            domain = domain
        )
    ```
        should return an empty string.

    * Example 3: Conditional and API in loop
    ```
        tool_policy_pseudo_code(
            policy_txt = "when buying a van, check that the van was never owned by someone from the buyer's family.",
            fn_to_analyze = "buy_car(plate_num: str, owner_id: str, insurance_id: str, payments: List[Payment])",
            domain = domain
        )
    ```
        should return:
    ```
        user = api.get_car(plate_num)
        if car.car_type == CarType.VAN:
            history = api.car_ownership_history(plate_num)
            for each ownership in history:
                assert(not api.are_relatives(ownership.owenr_id, owner_id))
    ```

    * Example 4: Last item
    ```
        tool_policy_pseudo_code(
            policy_txt = "when buying a van, check that the last payment method is using an active credit card.",
            fn_to_analyze = "buy_car(plate_num: str, owner_id: str, insurance_id: str, payments: List[Payment])",
            domain = domain
        )
    ```
        should return:
    ```
        user = api.get_person(owner_id)
        payment_method = user.payment_methods[payments[-1].payment_method_id]
        assert payment_method.active
        assert instanceof(payment_method, CreditCard)
    ```

    * Example 5: Refences in loop, and using instanceof
    ```
        tool_policy_pseudo_code(
            policy_txt = "when buying a van, check that the payments include exactly one cash and one credit card.",
            fn_to_analyze = "buy_car(plate_num: str, owner_id: str, insurance_id: str, payments: List[Payment])",
            domain = domain
        )
    ```
        should return:
    ```
        user = api.get_person(owner_id)
        cash_count = 0
        credit_card_count = 0
        for each payment in payments:
            payment_method = user.payment_methods[payment.payment_method_id]
            if instanceof(payment_method, Cash):
                cash_count += 1
            if instanceof(payment_method, CreditCard):
                credit_card_count += 1

        assert cash_count == 1
        assert credit_card_count == 1
    ```
    """
    ...
