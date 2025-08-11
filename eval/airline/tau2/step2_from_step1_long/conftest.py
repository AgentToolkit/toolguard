
import pytest

def pytest_runtest_protocol(item, nextitem):
    docstring = item.function.__doc__
    if docstring:
        item.user_properties.append(("docstring", docstring))
