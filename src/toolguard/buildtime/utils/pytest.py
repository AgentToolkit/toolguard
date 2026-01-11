from enum import StrEnum
import json
from pathlib import Path
from typing import Any, List, Dict, Optional
from pydantic import BaseModel, Field

from toolguard.buildtime.utils.multi_process import run_in_process
from toolguard.buildtime.utils.safe_py import run_safe_python
from toolguard.runtime.data_types import FileTwin


class TestOutcome(StrEnum):
    passed = "passed"
    failed = "failed"


class TracebackEntry(BaseModel):
    path: str
    lineno: int
    message: str


class CrashInfo(BaseModel):
    path: str
    lineno: int
    message: str


class CallInfo(BaseModel):
    duration: float
    outcome: TestOutcome
    crash: Optional[CrashInfo] = None
    traceback: Optional[List[TracebackEntry]] = None
    longrepr: Optional[str] = None


class TestPhase(BaseModel):
    duration: float
    outcome: TestOutcome


class TestResult(BaseModel):
    nodeid: str
    lineno: int
    outcome: TestOutcome
    keywords: List[str]
    setup: TestPhase
    call: CallInfo
    user_properties: Optional[List[Any]] = None
    teardown: TestPhase


class ResultEntry(BaseModel):
    nodeid: str
    type: str
    lineno: Optional[int] = None


class Collector(BaseModel):
    nodeid: str
    outcome: TestOutcome
    result: List[ResultEntry]
    longrepr: Optional[str] = None


class Summary(BaseModel):
    failed: Optional[int] = 0
    total: int
    collected: int


class TestReport(BaseModel):
    created: float
    duration: float
    exitcode: int
    root: str
    environment: Dict[str, str]
    summary: Summary
    collectors: List[Collector] = Field(default=[])
    tests: List[TestResult]

    def all_tests_passed(self) -> bool:
        return all([test.outcome == TestOutcome.passed for test in self.tests])

    def all_tests_collected_successfully(self) -> bool:
        return all([col.outcome == TestOutcome.passed for col in self.collectors])

    def non_empty_tests(self) -> bool:
        return self.summary.total > 0

    def list_errors(self) -> List[str]:
        errors = set()

        # Python errors in the function under test
        for col in self.collectors:
            if col.outcome == TestOutcome.failed and col.longrepr:
                errors.add(col.longrepr)

        # applicative test failure
        for test in self.tests:
            if test.outcome == TestOutcome.failed:
                error = test.call.longrepr
                if test.call.crash:
                    error = test.call.crash.message
                if test.user_properties:
                    case_desc = test.user_properties[0].get("docstring")
                    if case_desc and test.call.crash:
                        error = f"""Test case {case_desc} failed with the following message:\n {test.call.crash.message}"""
                if error:
                    errors.add(error)
        return list(errors)


def run(folder: Path, test_file: Path, report_file: Path) -> TestReport:
    run_tests_in_safe_python_separate_process(folder, test_file, report_file)

    report = read_test_report(folder / report_file)

    # overwrite it with indented version
    with open(folder / report_file, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2)

    return report


# Run the tests in this environment.
# run the tests in safe mode, so network and os operations are blocked. only specified libraries can be used.
# run the tests in a separate process. so python modules are isolated. as the code is evolving in the filesystem, we need a way to avoid python module caching. otherwise, it will not see that the code in the file has changed.
def run_tests_in_safe_python_separate_process(
    folder: Path, test_file: Path, report_file: Path
):
    code = f"""
import pytest
pytest.main(["{folder / test_file}", "--quiet", "--json-report", "--json-report-file={folder / report_file}"])
"""
    return run_in_process(run_safe_python, code, ["pytest"])


# def _run_in_subprocess(folder:str, test_file:str, report_file:str):
#     subprocess.run([
#             "pytest",
#             test_file,
#             # "--verbose",
#             "--quiet",
#             "--json-report",
#             f"--json-report-file={report_file}"
#         ],
#         env={
#             **os.environ,
#             "PYTHONPATH": "."
#         },
#         cwd=folder)


def configure(folder: Path):
    """adds the test function docstring to the output report"""

    hook = """
import pytest

def pytest_runtest_protocol(item, nextitem):
    docstring = item.function.__doc__
    if docstring:
        item.user_properties.append(("docstring", docstring))
"""
    FileTwin(file_name="conftest.py", content=hook).save(folder)


def read_test_report(file_path: Path) -> TestReport:
    with open(file_path, "r") as file:
        data = json.load(file)
    return TestReport.model_validate(data, strict=False)
