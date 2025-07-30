from pydantic import BaseModel, Field
import re

PYTHON_PATTERN = r'^```python\s*\n(def[\s\S]{10, 300})\n```'
class PythonCodeModel(BaseModel):
    python_code: str = Field(..., )
    def get_code_content(self) -> str:
        match = re.match(PYTHON_PATTERN, self.python_code)
        if match:
            return match.group(1)\
                .replace("\\n", "\n")
        return self.python_code
    
    @classmethod
    def create(cls, python_code: str) -> "PythonCodeModel":
        return PythonCodeModel.model_construct(python_code = f"```python\n{python_code}\n```")
