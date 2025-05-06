import os
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

from policy_adherence.utils import to_md_bulltets

class SourceFile(BaseModel):
    file_name: str
    content: str

    def save(self, folder:str):
        full_path = os.path.join(folder, self.file_name)
        parent = Path(full_path).parent
        os.makedirs(parent, exist_ok=True)
        with open(full_path, "w") as file:
            file.write(self.content)

    def save_as(self, folder:str, file_name:str):
        file_path = os.path.join(folder, file_name)
        with open(file_path, "w") as file:
            file.write(self.content)

    @staticmethod
    def load_from(folder:str, file_path:str)->'SourceFile':
        with open(os.path.join(folder, file_path), "r") as file:
            data = file.read()
            return SourceFile(
                file_name=file_path, 
                content=data
            )

class ToolPolicyItem(BaseModel):
    name: str
    description: str = Field(..., description="Policy item description")
    references: List[str] = Field(..., description="original text")
    compliance_examples: Optional[List[str]] = Field(..., description="Case example that complies with the policy")
    violation_examples: Optional[List[str]] = Field(..., description="Case example that violates the policy")

class ToolPolicy(BaseModel):
    name: str
    policy_items: List[ToolPolicyItem]
    
    def __str__(self) -> str:
        s = ""
        for i, item in enumerate(self.policy_items):
            s+= f"#### Policy item {i+1}\n"
            s+=f"{item.description}\n"
            if item.compliance_examples:
                s+=f"##### Positive examples\n{to_md_bulltets(item.compliance_examples)}"
            if item.violation_examples:
                s+=f"##### Negative examples\n{to_md_bulltets(item.violation_examples)}"
            s+="\n"
        return s


class ToolChecksCodeResult(BaseModel):
    tool: ToolPolicy
    tool_check_file: SourceFile
    item_check_files: List[SourceFile]
    test_files: List[SourceFile]

class ToolChecksCodeGenerationResult(BaseModel):
    output_path: str
    domain_file: str
    tools: Dict[str, ToolChecksCodeResult]
