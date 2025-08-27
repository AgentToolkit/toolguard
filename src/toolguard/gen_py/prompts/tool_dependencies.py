
from typing import Set
from toolguard.data_types import Domain, ToolPolicyItem
from programmatic_ai import generative


@generative
async def tool_dependencies(policy_item: ToolPolicyItem, fn_under_test_signature: str, domain: Domain) -> Set[str]:
    """
    Determine other tool names that the given tool depends on, based on its business policy.

    Args:
        policy_item (ToolPolicyItem): Business policy, in natural language, specifying a constraint on a process involving the tool under analysis.
        fn_under_test_signature (str): The function signature of the tool under analysis.
        domain (Domain): Python code defining available data types and APIs for invoking other tools.

    Returns:
        Set[str]: Names of tools that the analyzed tool depends on.

    Dependency Rules:
        - **Missing Information**: If enforcing a policy requires data not present in the tool’s function parameters,
          this data must be obtained by calling other tools or APIs.
        - **Direct Dependency**: A tool depends on another tool if that tool can be called directly to provide
          required data or perform necessary checks.
        - **Indirect Dependencies**:  
            - Dependencies may form chains, where one tool’s output serves as input for another.  
            - Some policies require multiple calls to the same tool, such as querying a data validation API for each item in a list.  
            - When policies involve updates, it is often necessary to compare the *existing* state with the *new* state. This typically results in at least two dependencies: one to retrieve the original data, and another to fetch up-to-date details about the new inputs.  
                For example, when updating a hotel reservation with new room IDs, you cannot rely on the reservation object to contain full details about those rooms. Instead, you would call `get_hotel_reservation` to obtain the existing reservation, and then call `get_room_details` for each new room to acquire current information.
        - **Immutable Source Constraint**: A tool may only depend on immutable (read only) tools.

    Examples:
        ```python
        domain = {
            "app_types": {
                "file_name": "car_types.py",
                "content": '''
                    class Car:
                        plate_num: str
                        previous_owner_ids: List[str]
                    class Person:
                        id: str
                        driving_licence: str
                    class Insurance:
                        doc_id: str
                '''
            },
            "app_api": {
                "file_name": "cars_api.py",
                "content": '''
                    class CarAPI(ABC):
                        def buy_car(self, plate_num: str, owner_id: str, insurance_id: str): pass
                        def get_person(self, id: str) -> Person: pass
                        def get_insurance(self, id: str) -> Insurance: pass
                        def get_car(self, plate_num: str) -> Car: pass
                        def delete_car(self, plate_num: str): pass
                        def list_all_cars_owned_by(self, id: str) -> List[Car]: pass
                        def are_relatives(self, person1_id: str, person2_id: str) -> bool: pass
                '''
            }
        }

        assert tool_dependencies(
            {"name": "documents exists", "description": "when buying a car, check that the car owner has a driving licence and that the insurance is valid."},
            "buy_car(plate_num: str, owner_id: str, insurance_id: str)",
            domain
        ) == {"get_person", "get_insurance"}

        assert tool_dependencies(
            {"name": "has driving licence", "description": "when buying a car, check that the car owner has a driving licence"},
            "buy_car(plate_num: str, owner_id: str, insurance_id: str)",
            domain
        ) == {"get_person"}

        assert tool_dependencies(
            {"name": "no transfers on holidays", "description": "when buying a car, check that it is not a holiday today"},
            "buy_car(plate_num: str, owner_id: str, insurance_id: str)",
            domain
        ) == {}

        # Indirect dependency. are_relatives() should be called multiple times.
        assert tool_dependencies(
            {"name": "Not in the same family", "description": "when buying a car, check that the car was never owned by someone from the buyer's family."},
            "buy_car(plate_num: str, owner_id: str, insurance_id: str)",
            domain
        ) == {"get_car", "are_relatives"}
        ```
    """
    ...
