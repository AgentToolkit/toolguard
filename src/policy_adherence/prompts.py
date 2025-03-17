
from typing import List
from policy_adherence.types import GenFile, ToolPolicy
from policy_adherence.utils import to_md_bulltets
from policy_adherence.llm.llm_model import LLM_model

def do_generate_tool_tests(llm: LLM_model, fn_name:str, fn_stub:GenFile, tool:ToolPolicy, domain:GenFile)-> str:
    prompt = f"""You are given:
* a Python file describing the domain. It contains data classes and interfaces you may use.
* a list of policy items. Policy items have a list of positive and negative examples. 
* an interface of a Python function-under-test, `{fn_name}()`.

Your task is to write unit tests to check the implementation of the interface-under-test.
The function implemtation should assert that ALL policy statements hold on its arguments.
If the arguments violate a policy statement, an exception should be thrown.
Policy statement have positive and negative examples.
For positive-cases, the function should not throw exceptions.
For negative-cases, the function should throw an exception.
Generate one test for each example. 

If an unexpected exception is catched, the test should fail with the nested exception message.

Name the test using up to 6 representative words (snake_case).

The function-under-test might call other functions, in the domain, to retreive data, and check the policy accordingly. 
Hence, you should MOCK the call to other functions and set the expected return value using `unittest.mock.patch`. 
For example, if `check_book_reservation` is the function-under-test, it may access the `get_user_details()`:
```
args = ...
user = User(...)
with patch("check_book_reservation.get_user_details", return_value=user):
check_book_reservation(args)
```

Make sure to indicate test failures using a meaningful message.

### Domain:
```python
### {domain.file_name}

{domain.content}
```

### Policy Items:

{tool.policies_to_md()}


### Interface under test
```python
### {fn_stub.file_name}

{fn_stub.content}
```"""
    return llm.generate(prompt)


def do_improve_fn(llm: LLM_model, fn_name:str, domain: GenFile, tool: ToolPolicy, previous_version:GenFile, review_comments: List[str])->str:
    prompt = f"""You are given:
* a Python file describing the domain. It contains data classes and functions you may use.
* a list of policy items. Policy items have a list of positive and negative examples. 
* current implementation of a Python function, `{fn_name}()`.
* a list of review comments on issues that need to be improved in the current implementation.

The goal of the function is to check that ALL policy items hold on the function arguments. 
In particular, running the function on all the positive examples should pass.
For all negative examples, the function should raise an exception with a meaningful message.

If you need to retrieve additional data (that is not in the function arguments), you can call functions defined in the domain.
You need to generate code that improve the current implementation, according to the review comments.
The code must be simple and well documented.

### Domain:
```python
### {domain.file_name}

{domain.content}
```

### Policy Items:

{tool.policies_to_md()}


### Current implemtnation
```python
### {previous_version.file_name}

{previous_version.content}
```

### Review commnets:

{to_md_bulltets(review_comments)}
"""
    return llm.generate(prompt)