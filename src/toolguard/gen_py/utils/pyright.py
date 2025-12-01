import json
import sys
import subprocess
from pydantic import BaseModel
from typing import List, Optional

from ...data_types import FileTwin

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

    def list_error_messages(self, file_content: str)->List[str]:
        msgs = set()
        for d in self.generalDiagnostics:
            if d.severity == ERROR:
                msgs.add(f"Syntax error: {d.message}.  code block: \'{get_text_by_range(file_content, d.range)}, \'")
        return list(msgs)

def get_text_by_range(file_content: str, rng: Range)-> str:
    lines = file_content.splitlines()

    if rng.start.line == rng.end.line:
        # Single-line span
        return lines[rng.start.line][rng.start.character:rng.end.character]

    # Multi-line span
    selected_lines = []
    selected_lines.append(lines[rng.start.line][rng.start.character:])  # First line, from start.character
    for line_num in range(rng.start.line + 1, rng.end.line):
        selected_lines.append(lines[line_num])            # Full middle lines
    selected_lines.append(lines[rng.end.line][:rng.end.character])      # Last line, up to end.character

    return "\n".join(selected_lines)


def run(folder:str, py_file:str)->DiagnosticsReport:
    py_path = sys.executable
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

def config(folder:str):
    cfg = {
        "typeCheckingMode": "basic",
        "reportOptionalIterable": WARNING,
        "reportArgumentType": WARNING, #"Object of type \"None\" cannot be used as iterable value",
        "reportOptionalMemberAccess": WARNING,
        "reportOptionalSubscript": WARNING,
        "reportAttributeAccessIssue": ERROR
    }
    FileTwin(file_name="pyrightconfig.json",
            content=json.dumps(cfg, indent=2)).save(folder)

if __name__ == '__main__':
    venv = "/Users/davidboaz/Documents/GitHub/gen_policy_validator/eval/airline/output/2025-08-04_15_52_00/my_env"
    folder= "/Users/davidboaz/Documents/GitHub/gen_policy_validator/eval/airline/output/2025-08-04_15_52_00/debug/cancel_reservation/cancellation_policy_for_all_flights"
    file = "0_test_guard_cancellation_policy_for_all_flights.py"

    content = FileTwin.load_from(folder, file).content
    r = run(folder, file, venv)
    for err in r.list_error_messages(content):
        print(err)
