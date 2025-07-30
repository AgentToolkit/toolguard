
from typing import List
from toolguard.data_types import FileTwin
from programmatic_ai import generative


@generative
async def tool_information_dependencies(tool_name: str, policy: str, domain: FileTwin)-> List[str]:
    """
    List other tools that the given tool depends on.

    Args:
        tool_name (str): name of the tool under analysis
        policy (str): business policy, in natural language, specifying a constraint on a business processes involving the tool unedr analysis
        domain (FileTwin): Python code defining available data types and other tool interfaces

    Returns:
        Set[str]: dependent tool names

    **Dependency Rules:**
    - Tool available information is: from it function arguments, or from calling other tools.
    - The function analyzes information dependency only on other tools.
    - Information dependency can be only on tools that are immutable. That is, that retieve data only, but do not modify the environment.
    - A dependency in another-tool exists only if the policy mention information is not available in the arguments, but can accessed by calling the other tool.
    - The set of dependencies can be empty, with one, or multiple tools.
    
    **Example: ** 
```python
    domain = {
        "file_name": "domain.py",
        "content": "
    class Car:
        pass
    class Person:
        pass
    class Insurance:
        pass
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

    # According to the policy, the `buy_car` operation depends on `get_person` to get the driving licence of the owner, and on `get_insurance` to check the insurance is valid.
    assert tool_dependencies(
        "tool_name": "buy_car", 
        "policy": "when buying a new car, you should check that the car owner has a driving licence and that the insurance is valid.",
        "domain": domain
    ) == {"get_person", "get_insurance"}

    # According to the policy, the `get_insurance` operation does not depend on any other operation
    assert tool_dependencies(
        "tool_name": "get_insurance", 
        "policy": "when buying a new car, you should check that the car owner has a driving licence and that the insurance is valid.",
        "domain": domain
    ) == {}

    # According to the policy, the `delete_car` operation does not depend on any other operation
    assert tool_dependencies(
        "tool_name": "delete_car", 
        "policy": "when buying a new car, you should check that the car owner has a driving licence and that the insurance is valid.",
        "domain": domain
    ) == {}

```

    """
    ...
