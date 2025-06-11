import os
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Dict, List, Optional


def to_md_bulltets(items: List[str])->str:
    s = ""
    for item in items:
        s+=f"* {item}\n"
    return s

class FileTwin(BaseModel):
    file_name: str
    content: str

    def save(self, folder:str):
        full_path = os.path.join(folder, self.file_name)
        parent = Path(full_path).parent
        os.makedirs(parent, exist_ok=True)
        with open(full_path, "w") as file:
            file.write(self.content)

    def save_as(self, folder:str, file_name:str)->'FileTwin':
        file_path = os.path.join(folder, file_name)
        with open(file_path, "w") as file:
            file.write(self.content)
        return FileTwin(file_name=file_name, content=self.content)

    @staticmethod
    def load_from(folder:str, file_path:str)->'FileTwin':
        with open(os.path.join(folder, file_path), "r") as file:
            data = file.read()
            return FileTwin(
                file_name=file_path, 
                content=data
            )

class ToolPolicyItem(BaseModel):
    name: str
    description: str = Field(..., description="Policy item description")
    references: List[str] = Field(..., description="original text")
    compliance_examples: Optional[List[str]] = Field(..., description="Case example that complies with the policy")
    violation_examples: Optional[List[str]] = Field(..., description="Case example that violates the policy")

    def __str__(self) -> str:
        s = f"#### Policy item " + self.name + "\n"
        s += f"{self.description}\n"
        if self.compliance_examples:
            s += f"##### Positive examples\n{to_md_bulltets(self.compliance_examples)}"
        if self.violation_examples:
            s += f"##### Negative examples\n{to_md_bulltets(self.violation_examples)}"
        return s
        

class ToolPolicy(BaseModel):
    name: str
    policy_items: List[ToolPolicyItem]

class ToolChecksCodeResult(BaseModel):
    tool: ToolPolicy
    tool_check_file: FileTwin
    item_check_files: List[FileTwin|None]
    test_files: List[FileTwin|None]

class ToolChecksCodeGenerationResult(BaseModel):
    output_path: str
    domain_file: str
    tools: Dict[str, ToolChecksCodeResult]
