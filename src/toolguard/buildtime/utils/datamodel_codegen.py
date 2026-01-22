from pathlib import Path
import subprocess


def run(oas_file: Path):
    # see https://github.com/koxudaxi/datamodel-code-generator
    res = subprocess.run(
        [
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
            oas_file,
            # "--output", domain_file
        ],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise Exception(res.stderr)
    return res.stdout
