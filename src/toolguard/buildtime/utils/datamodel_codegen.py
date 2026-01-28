import asyncio
from pathlib import Path


async def run(oas_file: Path) -> str:
    """Run datamodel-codegen to generate Pydantic models from OpenAPI spec.

    Args:
        oas_file: Path to the OpenAPI specification file.

    Returns:
        Generated Python code as a string, or empty string if no models found.

    Raises:
        RuntimeError: If datamodel-codegen fails with an error.
    """
    # see https://github.com/koxudaxi/datamodel-code-generator
    process = await asyncio.create_subprocess_exec(
        "datamodel-codegen",
        "--use-field-description",
        "--use-schema-description",
        "--output-model-type",
        "pydantic_v2.BaseModel",  # "typing.TypedDict",
        "--collapse-root-models",
        # "--force-optional",
        "--reuse-model",  # https://github.com/koxudaxi/datamodel-code-generator/blob/4661406431a17b17c2ad0335589bcb12123fd45d/docs/model-reuse.md
        "--enum-field-as-literal",
        "all",
        "--input-file-type",
        "openapi",
        "--use-operation-id-as-name",
        "--openapi-scopes",
        "paths",
        "parameters",
        "schemas",
        "--input",
        str(oas_file),
        # "--output", domain_file
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        stderr_text = stderr.decode()
        if "Models not found in the input data" in stderr_text:
            # Legitimate: spec has no schemas
            return ""  # an empty file
        raise RuntimeError(f"datamodel-codegen failed:\n{stderr_text}")
    return stdout.decode()
