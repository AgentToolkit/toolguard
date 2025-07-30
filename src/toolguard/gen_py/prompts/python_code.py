from pydantic import BaseModel, Field
import re

PYTHON_PATTERN = r'^```python\s*\n([\s\S]+?)\n```$'
class PythonCodeModel(BaseModel):
    python_code: str = Field(
        ...,
        pattern=PYTHON_PATTERN,
        min_length= 10,
        max_length= 300,
    )
    def get_code_content(self) -> str:
        match = re.match(PYTHON_PATTERN, self.python_code)
        if match:
            return match.group(1)\
                .replace("\\n", "\n")
        return self.python_code
    
    @classmethod
    def create(cls, python_code: str) -> "PythonCodeModel":
        return PythonCodeModel.model_construct(python_code = f"```python\n{python_code}\n```")
