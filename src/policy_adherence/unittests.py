
import json
import os
import subprocess
from typing import List, Dict, Optional
from pydantic import BaseModel

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
    outcome: str
    crash: Optional[CrashInfo] = None
    traceback: Optional[List[TracebackEntry]] = None
    longrepr: Optional[str] = None

class TestPhase(BaseModel):
    duration: float
    outcome: str

class TestResult(BaseModel):
    nodeid: str
    lineno: int
    outcome: str
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
    outcome: str
    result: List[ResultEntry]

class Summary(BaseModel):
    failed: Optional[int]
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

def run_unittests(folder:str)->TestReport:
    report_file = "pytest_report.json"
    subprocess.run([
            "pytest", 
            "--json-report", 
            f"--json-report-file={report_file}"
        ], 
        cwd=folder)

    with open(os.path.join(folder, report_file), "r") as file:
        data = json.load(file)
    return TestReport(**data)
    
    