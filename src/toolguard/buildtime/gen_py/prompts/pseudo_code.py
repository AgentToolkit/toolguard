# mypy: ignore-errors


from mellea import generative

from toolguard.runtime.data_types import FileTwin


@generative
async def tool_policy_pseudo_code(
    policy_txt: str, fn_to_analyze: str, data_types: FileTwin, api: FileTwin
) -> str:
    """
            Returns a pseudo code to check business constraints on `fn_to_analyze` calls using an API.

            Args:
                policy_txt (str): Business policy, in natural language, specifying a constraint on a process involving the tool under analysis.
                fn_to_analyze (str): The function signature of the tool under analysis.
                data_types (FileTwin): Python code defining available data types.
                api (FileTwin): Python code defining available APIs.

            Returns:
                str: A pseudo code descibing how to validate `fn_to_analyze` calls complies with the policy.

            * Use the API methods, or Python builtin function to enforce the policy, when calling `fn_to_analyze`.
            * Do not assume other API functions.
            * If the policy references information that is not explicitly provided as a `fn_to_analyze` parameter, use the available API functions to retrieve the missing data (for example, by fetching resources by ID).
            * Use the type hints (in `data_types`) to determine parameters and returned value data types.
                * You can access only the fields declared in the types. Otherwise a syntax error occur.
                * Do not assume the presence of any additional fields.
                * Do not assume any implicit logic or relationships between field values (e.g., do not assume naming conventions).

            Examples:
        ```python
    data_types = {
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
    "api": {
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
    ```
    * Example 1: retrieve data by ID
    ```
        tool_policy_pseudo_code(
            policy_txt = "when buying a car, check that the car owner has a driving licence and that the insurance is valid.",
            fn_to_analyze = "buy_car(plate_num: str, owner_id: str, insurance_id: str, payments: List[Payment])",
            data_types = data_types,
            api = api
        )
    ```
    returns:
    ```
        user = api.get_person(owner_id)
        assert user.driving_licence
        insurance = api.get_insurance(insurance_id)
        assert insurance.valid
    ```

    * Example 2: Empty response when there are no relevant API to check the policy
    ```
        tool_policy_pseudo_code(
            policy_txt = "when buying a car, check that it is not a holiday today",
            fn_to_analyze = "buy_car(plate_num: str, owner_id: str, insurance_id: str, payments: List[Payment])",
            data_types = data_types,
            api = api
        )
    ```
    returns: ""

    * Example 3: Policy with condition and API in loop
    ```
        tool_policy_pseudo_code(
            policy_txt = "when buying a van, check that the van was never owned by someone from the buyer's family.",
            fn_to_analyze = "buy_car(plate_num: str, owner_id: str, insurance_id: str, payments: List[Payment])",
            data_types = data_types,
            api = api
        )
    ```
    returns:
    ```
        user = api.get_car(plate_num)
        if car.car_type == CarType.VAN:
            history = api.car_ownership_history(plate_num)
            for each ownership in history:
                relatives = api.are_relatives(ownership.owenr_id, owner_id)
                assert not relatives
    ```

    * Example 4: Policy on the last item in a collection
    ```
        tool_policy_pseudo_code(
            policy_txt = "when buying a van, check that the last payment is using an active credit card.",
            fn_to_analyze = "buy_car(plate_num: str, owner_id: str, insurance_id: str, payments: List[Payment])",
            data_types = data_types,
            api = api
        )
    ```
    returns:
    ```
        user = api.get_person(owner_id)
        payment_method = user.payment_methods[payments[-1].payment_method_id]
        assert instanceof(payment_method, CreditCard)
        assert payment_method.active
    ```

    * Example 5: Refences in loop, and using instanceof
    ```
        tool_policy_pseudo_code(
            policy_txt = "when buying a van, check that the payments include exactly one cash and one credit card.",
            fn_to_analyze = "buy_car(plate_num: str, owner_id: str, insurance_id: str, payments: List[Payment])",
            data_types = data_types,
            api = api
        )
    ```
    returns:
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
