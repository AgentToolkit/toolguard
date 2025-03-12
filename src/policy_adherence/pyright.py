import json
import subprocess
from pydantic import BaseModel
from typing import List, Optional

ERROR = "error"

class Position(BaseModel):
    line: Optional[int] = None
    character: Optional[int] = None

class Range(BaseModel):
    start: Optional[Position] = None
    end: Optional[Position] = None

class GeneralDiagnostic(BaseModel):
    file: Optional[str] = None
    severity: Optional[str] = None
    message: Optional[str] = None
    range: Optional[Range] = None
    rule: Optional[str] = None

class Summary(BaseModel):
    filesAnalyzed: Optional[int] = None
    errorCount: Optional[int] = None
    warningCount: Optional[int] = None
    informationCount: Optional[int] = None
    timeInSec: Optional[float] = None

class DiagnosticsReport(BaseModel):
    version: Optional[str] = None
    time: Optional[str] = None  # Keeping as string to preserve timestamp format
    generalDiagnostics: Optional[List[GeneralDiagnostic]] = None
    summary: Optional[Summary] = None

    def list_errors(self)->Optional[List[str]]:
        if self.generalDiagnostics:
            return [d.message for d 
                in self.generalDiagnostics
                if d.severity in [ERROR]] # type: ignore

def run_pyright(folder:str, py_file:str)->DiagnosticsReport:
    res = subprocess.run([
            "pyright", 
            "--outputjson",
            py_file
        ], 
        cwd=folder,
        capture_output=True, 
        text=True
    )
    data = json.loads(res.stdout)
    return DiagnosticsReport.model_validate(data)

# r = run_pyright("/Users/davidboaz/Documents/GitHub/gen_policy_validator/tau_airline/output/2025-03-12 14:26:15", 
#     "test_check_book_reservation.py")
# print(r)