
from enum import StrEnum
import json
import os
import subprocess
from typing import List, Dict, Literal, Optional
from pydantic import BaseModel


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
    teardown: TestPhase

class ResultEntry(BaseModel):
    nodeid: str
    type: str
    lineno: Optional[int] = None

class Collector(BaseModel):
    nodeid: str
    outcome: TestOutcome
    result: List[ResultEntry]

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
    collectors: List[Collector]
    tests: List[TestResult]

    def all_tests_passed(self)->bool:
        return all([test.outcome == TestOutcome.passed for test in self.tests])
    
    def all_tests_collected_successfully(self)->bool:
        return all([col.outcome == TestOutcome.passed for col in self.collectors])
    
    def list_errors(self)->List[str]:
        errors = []
        for test in self.tests:
            if test.outcome == TestOutcome.failed:
                errors.append(test.call.crash.message)
        return errors

def run_unittests(folder:str)->TestReport:
    report_file = "pytest_report.json"
    subprocess.run([
            "pytest", 
            "--json-report", 
            f"--json-report-file={report_file}"
        ], 
        cwd=folder)
    return read_test_report(os.path.join(folder, report_file))

def read_test_report(file_path:str)->TestReport:
    with open(file_path, "r") as file:
        data = json.load(file)
    return TestReport.model_validate(data, strict=False)

# report = read_test_report("/Users/davidboaz/Documents/GitHub/gen_policy_validator/tau_airline/output/2025-03-12 08:54:16/pytest_report.json")
# print(report.summary.failed)