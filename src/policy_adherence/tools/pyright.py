import json
import subprocess
from pydantic import BaseModel
from typing import List, Optional

from policy_adherence.types import MyFile

ERROR = "error"

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
    rule: str

    def is_error(self)->bool:
        #all fields in the generated domain are optional. 
        #The generated tests set the field values, and then try to access them. This is safe 
        # but pyright consider this as error
        if "None" in self.message: 
            return False
        
        return self.severity in [ERROR]
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

    def errors_only(self)->List[GeneralDiagnostic]:        
        if self.generalDiagnostics:
            return [d for d in self.generalDiagnostics if d.is_error()]
        return []
    
    def copy_errors_only(self)->'DiagnosticsReport':
        errs = self.errors_only() 
        return DiagnosticsReport(
            **self.model_dump(exclude={"generalDiagnostics", "summary"}),
            generalDiagnostics = errs,
            summary=Summary(
                **self.summary.model_dump(exclude={"errorCount"}),
                # filesAnalyzed
                errorCount = len(errs)
                # warningCount
                # informationCount
                # timeInSec
            )
        )

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
    original = DiagnosticsReport.model_validate(data)
    return original.copy_errors_only()

# def pyright_config() ->MyFile:
#     cfg = {
#         "typeCheckingMode": "basic",
#         "reportOptionalIterable": "warning",
#         "reportArgumentType": "warning", #"Object of type \"None\" cannot be used as iterable value",
#     }
#     return MyFile(file_name="pyrightconfig.json",
#                   content=json.dumps(cfg, indent=2))

# r = run_pyright("/Users/davidboaz/Documents/GitHub/gen_policy_validator/tau_airline/output/2025-03-12 14:26:15", 
#     "test_check_book_reservation.py")
# print(r)