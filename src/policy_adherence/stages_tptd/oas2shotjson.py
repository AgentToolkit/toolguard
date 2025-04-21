import copy
import json

import yaml

from policy_adherence.common.dict import substitute_refs
from policy_adherence.common.open_api import OpenAPI, PathItem, Operation


def read_oas(file_path:str)->OpenAPI:
    with open(file_path, "r") as file:
        d = yaml.safe_load(file)
    return OpenAPI.model_validate(d)

def op_only_oas(oas: OpenAPI, operationId: str)-> OpenAPI:
    new_oas = OpenAPI(
        openapi=oas.openapi,
        info=oas.info,
        #components=oas.components
    )
    for path, path_item in oas.paths.items():
        for mtd, op in path_item.operations.items():
            if op.operationId == operationId:
                if new_oas.paths.get(path) is None:
                    new_oas.paths[path] = PathItem(
                        summary=path_item.summary,
                        description=path_item.description,
                        servers=path_item.servers,
                        parameters=path_item.parameters,
                    ) # type: ignore
                setattr(
                    new_oas.paths.get(path),
                    mtd.lower(),
                    #copy.deepcopy(op)
                    Operation(**(substitute_refs(op.model_dump())))
                )
                
    return new_oas

def remove_nulls(data):
    """
    Recursively remove all None values from a nested dictionary or list.
    """
    if isinstance(data, dict):
        return {k: remove_nulls(v) for k, v in data.items() if v is not None and remove_nulls(v) != {}}
    elif isinstance(data, list):
        return [remove_nulls(v) for v in data if v is not None]
    else:
        return data

oas_file = '/Users/naamazwerdling/Documents/OASB/policy_validation/airline/openapi.yaml'
oas = read_oas(oas_file)


for path, path_item in oas.paths.items():
    for mtd, op in path_item.operations.items():
        opoas = op_only_oas(oas,op.operationId)
        print(op.operationId)
        newoas = json.loads(opoas.model_dump_json())
        print(opoas.model_dump_json())
        dict = remove_nulls(newoas)
        print(dict)

