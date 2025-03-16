
from loguru import logger
from policy_adherence.types import GenFile
from policy_adherence.common.open_api import OpenAPI
from policy_adherence.tools.pyright import run_pyright
from policy_adherence.utils import extract_code_from_llm_response


def generate_domain_old(self, oas: OpenAPI, retries=2)->GenFile:
        logger.debug(f"Generating domain... (retry = {retries})")
        prompt = f"""Given an OpenAPI Spec, generate Python code that include all the data-types as Pydantic data-classes. 
For data-classes fields, make all fields optional with default `None`.
For each operation, create a function stub.
The function name comes from the operation operationId.
The function argument names and types come from the operation parameters and requestBody.
The function return-type comes from the operation 200 response.
Both, the function arguments and return-type, should be specific (avoid Dict), and should refer to the generated data-classes.
Add the operation description as the function documentation.

```
{oas.model_dump_json(indent=2)}
```"""
        res_content = self._call_llm(prompt)
        body = extract_code_from_llm_response(res_content)
        domain = GenFile(file_name="domain.py", content=body)
        domain.save(self.cwd)
        lint_report = run_pyright(self.cwd, domain.file_name)
        if lint_report.list_errors():
            logger.warning(f"Generated domain have Python errors.")
            if retries>1:
                return self.generate_domain(oas, retries=retries-1) #retry
            raise Exception("Failed to generate domain from OpenAPI spec")
        return domain
