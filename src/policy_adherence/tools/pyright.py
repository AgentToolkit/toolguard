import json
import os
import subprocess
from pydantic import BaseModel
from typing import List, Optional

from policy_adherence.data_types import FileTwin

ERROR = "error"
WARNING = "warning"

class Position(BaseModel):
    line: int
    character: int

class Range(BaseModel):
    start: Position
    end: Position

class GeneralDiagnostic(BaseModel):
    file: str
    severity: str
    message: str
    range: Range
    rule: Optional[str] = None

class Summary(BaseModel):
    filesAnalyzed: int
    errorCount: int
    warningCount: int
    informationCount: int
    timeInSec: float

class DiagnosticsReport(BaseModel):
    version: str
    time: str
    generalDiagnostics: List[GeneralDiagnostic] 
    summary: Summary

    def list_error_messages(self)->List[str]:
        return list(set(d.message for d in self.generalDiagnostics if d.severity == ERROR))

def run(folder:str, py_file:str, venv_name:str)->DiagnosticsReport:
    py_path = os.path.join(venv_name, "bin", "python3")
    res = subprocess.run([
            "pyright", 
            # "--venv-path", venv_path,
            "--pythonpath", py_path,
            "--outputjson",
            py_file
        ], 
        cwd=folder,
        capture_output=True, 
        text=True
    )
    # if res.returncode !=0:
    #     raise Exception(res.stderr)
    
    data = json.loads(res.stdout)
    return DiagnosticsReport.model_validate(data)
    # return original.copy_errors_only()
    

def config() ->FileTwin:
    cfg = {
        "typeCheckingMode": "basic",
        "reportOptionalIterable": WARNING,
        "reportArgumentType": WARNING, #"Object of type \"None\" cannot be used as iterable value",
        "reportOptionalMemberAccess": WARNING,
        "reportAttributeAccessIssue": ERROR
    }
    return FileTwin(file_name="pyrightconfig.json",
                  content=json.dumps(cfg, indent=2))

# if __name__ == '__main__':
#     r = run_pyright("/Users/davidboaz/Documents/GitHub/gen_policy_validator/tau_airline/output/2025-03-16 14:44:43", "check_book_reservation.py")
#     print(r)