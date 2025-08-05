
from typing import List, Set
from toolguard.data_types import Domain, FileTwin, ToolPolicyItem
from programmatic_ai import generative


@generative
async def tool_dependencies(policy_item: ToolPolicyItem, domain: Domain)-> Set[str]:
    """
    Lists other tools that the given tool depends on.

    Args:
        policy_item (ToolPolicyItem): business policy, in natural language, specifying a constraint on a business processes involving the tool unedr analysis
        domain (Domain): Python code defining available data types and API to invoke other tools

    Returns:
        Set[str]: dependent tool names

    **Dependency Rules:**
    - Tool available information is: its function arguments, or the response of calling other tools .
    - The function analyzes information dependency only on other tools.
    - Information dependency can be only on tools that are immutable. That is, that retieve data only, but do not modify the environment.
    - A dependency in another-tool exists only if the policy mention information is not available in the arguments, but can accessed by calling the other tool.
    - The set of dependencies can be empty, with one, or multiple tools.
    
    **Example: ** 
```python
    domain = {
        "app_api":{
            "file_name": "car_types.py",
            "content": "
                class Car:
                    pass
                class Person:
                    driving_licence: str
                class Insurance:
                    pass
                "
        },
        "app_api":{
            "file_name": "cars_api.py",
            "content": "
                class CarAPI(Protocol):
                    def buy_car(self, car:Car, owner_id:str, insurance_id:str):
                        pass
                    def get_person(self, id:str) -> Person:
                        pass
                    def get_insurance(self, id:str) -> Insurance:
                        pass
                    def delete_car(self, car:Car):
                        pass
                    def list_all_cars_owned_by(self, id:str): List[Car]
                        pass
                "
        }
    }

    assert tool_dependencies(
        {
            "name": "documents exists",
            "description": "when buying a new car, you should check that the car owner has a driving licence and that the insurance is valid.",
        }
        "domain": domain
    ) == {"get_person", "get_insurance"}

    
    assert tool_dependencies(
        {
            "name": "documents exists",
            "description": "when buying a new car, you should check that the car owner has a driving licence",
        }
        "domain": domain
    ) == {"get_person"}

    assert tool_dependencies(
        {
            "name": "documents exists",
            "description": "when buying a new car, you should check that the insurance is valid.",
        }
        "domain": domain
    ) == {"get_insurance"}

    assert tool_dependencies(
        {
            "name": "documents exists",
            "description": "when buying a new car, you need to check that it is not a holiday today",
        }
        "domain": domain
    ) == {}
```

    """
    ...
