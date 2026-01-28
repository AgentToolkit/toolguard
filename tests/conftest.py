import os
import sys

import pytest
from dotenv import load_dotenv
from loguru import logger


@pytest.fixture(scope="session", autouse=True)
def load_env_once():
    """Automatically load .env before any tests."""
    load_dotenv()


def configure_loguru_for_tests() -> None:
    logger.remove()

    level = os.getenv("LOG_LEVEL", "DEBUG")

    logger.add(
        sys.stderr,  # pytest captures this; tee-sys will display it live
        level=level,
        enqueue=False,  # important for pytest reliability
        backtrace=False,  # cleaner test output
        diagnose=False,  # cleaner test output
        format="{time:HH:mm:ss} [{level:<8}] {name}:{function}:{line} - {message}",
    )


@pytest.fixture(scope="session", autouse=True)
def _loguru_session_setup() -> None:
    configure_loguru_for_tests()
