import pytest
from dotenv import load_dotenv


@pytest.fixture(scope="session", autouse=True)
def load_env_once():
    """Automatically load .env before any tests."""
    load_dotenv()
