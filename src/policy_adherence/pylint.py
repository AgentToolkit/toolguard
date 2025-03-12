
import json
import subprocess
from typing import Any, List

from typing import Optional
from pydantic import BaseModel, RootModel

TYPE_ERROR = "error"
TYPES_SEVERE = [TYPE_ERROR]

class PylintMessage(BaseModel):
    type: Optional[str] = None
    module: Optional[str] = None
    obj: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    path: Optional[str] = None
    symbol: Optional[str] = None
    message: Optional[str] = None
    messageId: Optional[str] = None
    confidence: Optional[str] = None
    endLine: Optional[int] = None
    endColumn: Optional[int] = None
    absolutePath: Optional[str] = None

class PylintReport(RootModel[List[PylintMessage]]):
    def list_errors(self):
        return [item.message for item in self.root if item.type in TYPES_SEVERE]

def run_pylint(folder:str, file:str)->PylintReport:
    disable = "C,R,W" #Convension, Refactor, Warning
    res = subprocess.run([
            "pylint", 
            "--output-format=json2",
            f"--disable={disable}",
            file
        ], 
        cwd=folder,
        capture_output=True, 
        text=True
    )
    data = json.loads(res.stdout)
    return PylintReport.model_validate(data.get("messages"))
