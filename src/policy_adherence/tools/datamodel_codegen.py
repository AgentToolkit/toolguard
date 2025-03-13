import subprocess


def run(oas_file:str, domain_file:str):
    #see https://github.com/koxudaxi/datamodel-code-generator
    res = subprocess.run([
            "datamodel-codegen",
            "--use-field-description",
            "--use-schema-description",
            "--use-operation-id-as-name",
            "--output-model-type", "pydantic_v2.BaseModel", #"typing.TypedDict",
            "--force-optional",
            "--reuse-model",
            "--input", oas_file,
            "--output", domain_file
        ], 
        # cwd=self.cwd,
        capture_output=True, 
        text=True
    )
    if res.returncode != 0:
        raise Exception(res.stderr)