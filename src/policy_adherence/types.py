import os
from pydantic import BaseModel, Field, RootModel
from typing import Dict, List, Optional, Tuple

from policy_adherence.utils import to_md_bulltets

class MyFile(BaseModel):
    file_name: str
    content: str

    def save(self, folder:str):
        file_path = os.path.join(folder, self.file_name)
        with open(file_path, "w") as file:
            file.write(self.content)

    def save_as(self, folder:str, file_name:str):
        file_path = os.path.join(folder, file_name)
        with open(file_path, "w") as file:
            file.write(self.content)


class ToolPolicyItem(BaseModel):
    policy: str = Field(..., description="Policy item")
    compliance_examples: Optional[List[str]] = Field(..., description="Case example that complies with the policy")
    violation_examples: Optional[List[str]] = Field(..., description="Case example that violates the policy")

class ToolPolicy(BaseModel):
    name: str
    policy_items:  List[ToolPolicyItem]
    
    def policies_to_md(self):
        s = ""
        for i, item in enumerate(self.policy_items):
            s+= f"#### Policy item {i+1}\n"
            s+=f"{item.policy}\n"
            if item.compliance_examples:
                s+=f"##### Positive examples\n{to_md_bulltets(item.compliance_examples)}"
            if item.violation_examples:
                s+=f"##### Negative examples\n{to_md_bulltets(item.violation_examples)}"
            s+="\n"
        return s
    
class ToolsPolicies(RootModel[List[ToolPolicy]]):
    pass
