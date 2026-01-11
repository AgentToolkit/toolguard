from toolguard.buildtime.utils.llm_py import get_code_content


def test_llm_python1():
    res = '```python\nfrom typing import *\n\nimport calc_fns\nfrom rt_toolguard.runtime import PolicyViolationException\nfrom calc_fns.calc_fns_types import *\nfrom calc_fns.i_calc_fns import I_CalcFns\n\ndef guard_division_by_zero_constraint(api: I_CalcFns, g: float, h: float):\n    """\n    Policy to check: The calculator must not allow division by zero. If a user attempts to divide by zero, the operation must be rejected and an appropriate error message should be shown (e.g., \'Error: Division by zero is not allowed.\').\n\n    Args:\n        api (I_CalcFns): api to access other tools.\n        g (float): The dividend.\n        h (float): The divisor (must not be zero).\n        \n    Raises:\n        PolicyViolationException: If division by zero is attempted.\n    """\n    if h == 0:\n        raise PolicyViolationException("Error: Division by zero is not allowed.")\n```'
    clean = get_code_content(res)
    assert clean.startswith("from typing")


def test_llm_python2():
    res = 'python\nfrom typing import *\n\nimport calc_fns\nfrom rt_toolguard.runtime import PolicyViolationException\nfrom calc_fns.calc_fns_types import *\nfrom calc_fns.i_calc_fns import I_CalcFns\n\ndef guard_division_by_zero_constraint(api: I_CalcFns, g: float, h: float):\n    """\n    Policy to check: The calculator must not allow division by zero. If a user attempts to divide by zero, the operation must be rejected and an appropriate error message should be shown (e.g., \'Error: Division by zero is not allowed.\').\n\n    Args:\n        api (I_CalcFns): api to access other tools.\n        g (float): The dividend.\n        h (float): The divisor (must not be zero).\n        \n    Raises:\n        PolicyViolationException: If division by zero is attempted.\n    """\n    if h == 0:\n        raise PolicyViolationException("Error: Division by zero is not allowed.")\n'
    clean = get_code_content(res)
    assert clean.startswith("from typing")


def test_llm_python3():
    res = 'from typing import *\n\nimport calc_fns\nfrom rt_toolguard.runtime import PolicyViolationException\nfrom calc_fns.calc_fns_types import *\nfrom calc_fns.i_calc_fns import I_CalcFns\n\ndef guard_division_by_zero_constraint(api: I_CalcFns, g: float, h: float):\n    """\n    Policy to check: The calculator must not allow division by zero. If a user attempts to divide by zero, the operation must be rejected and an appropriate error message should be shown (e.g., \'Error: Division by zero is not allowed.\').\n\n    Args:\n        api (I_CalcFns): api to access other tools.\n        g (float): The dividend.\n        h (float): The divisor (must not be zero).\n        \n    Raises:\n        PolicyViolationException: If division by zero is attempted.\n    """\n    if h == 0:\n        raise PolicyViolationException("Error: Division by zero is not allowed.")'
    clean = get_code_content(res)
    assert clean.startswith("from typing")
