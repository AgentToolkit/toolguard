import os
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Tuple

class Code(BaseModel):
    file_name: str
    content: str

    def save(self, folder:str):
        os.makedirs(folder, exist_ok=True)
        file_path = os.path.join(folder, self.file_name)
        with open(file_path, "w") as file:
            file.write(self.content)