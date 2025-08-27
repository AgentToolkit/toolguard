
from typing import Set
from toolguard.data_types import Domain, ToolPolicyItem
from programmatic_ai import generative


@generative
async def tool_policy_pseudo_code(policy_item: ToolPolicyItem, fn_to_analyze: str, domain: Domain) -> str:
    """
    Returns a pseudo code to check business constraints on a tool cool using an API

    Args:
        policy_item (ToolPolicyItem): Business policy, in natural language, specifying a constraint on a process involving the tool under analysis.
        fn_to_analyze (str): The function signature of the tool under analysis.
        domain (Domain): Python code defining available data types and APIs for invoking other tools.

    Returns:
        str: A pseudo code descibing how to use the API to check the tool call

    You must list all the required API calls. You should analyze the tool's signatures and parameters passing. If needed, show the chain of calls.    
    
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
```
* Example 1:
```
    tool_policy_pseudo_code(
        {"name": "documents exists", "description": "when buying a car, check that the car owner has a driving licence and that the insurance is valid."},
        "buy_car(plate_num: str, owner_id: str, insurance_id: str)",
        domain
    )
``` 
may return: 
```
    assert api.get_person(owner_id).driving_licence
    assert api.get_insurance(insurance_id)
```

* Example 2:
```
    tool_policy_pseudo_code(
        {"name": "has driving licence", "description": "when buying a car, check that the car owner has a driving licence"},
        "buy_car(plate_num: str, owner_id: str, insurance_id: str)",
        domain
    )
```
    may return: 
```
    assert api.get_insurance(insurance_id)
```

* Example 3:
```
    tool_policy_pseudo_code(
        {"name": "no transfers on holidays", "description": "when buying a car, check that it is not a holiday today"},
        "buy_car(plate_num: str, owner_id: str, insurance_id: str)",
        domain
    )
``` 
    should return an empty string.

* Example 4:
```
    tool_policy_pseudo_code(
        {"name": "Not in the same family", "description": "when buying a car, check that the car was never owned by someone from the buyer's family."},
        "buy_car(plate_num: str, owner_id: str, insurance_id: str)",
        domain
    )
``` 
    should return: 
```
    car = api.get_car(plate_num)
    for each prev_owner_id in car.previous_owner_ids:
        assert(not api.are_relatives(prev_owner_id, owner_id))
```
"""
    ...
