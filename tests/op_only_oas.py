
from policy_adherence.common.dict import substitute_refs
from policy_adherence.common.open_api import *

def clean_nulls_and_keys(data):
    if isinstance(data, dict):
        new_dict = {}
        for key, value in data.items():
            # Remove trailing underscore from key
            new_key = key.rstrip('_')
            cleaned_value = clean_nulls_and_keys(value)
            if cleaned_value is not None:
                new_dict[new_key] = cleaned_value
        return new_dict if new_dict else None
    elif isinstance(data, list):
        new_list = [clean_nulls_and_keys(item) for item in data]
        new_list = [item for item in new_list if item is not None]
        return new_list if new_list else None
    else:
        return data if data is not None else None
    
def op_only_oas(oas: OpenAPI, operationId: str)-> OpenAPI:
    new_oas = OpenAPI(
        openapi=oas.openapi, 
        info=oas.info,
        # components=oas.components
    )
    for path, path_item in oas.paths.items():
            path_item = oas.resolve_ref(path_item, PathItem)
            for mtd, op in path_item.operations.items():
                op = oas.resolve_ref(op, Operation)
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
                        Operation(**(substitute_refs(op.model_dump(by_alias=True), oas.model_dump(by_alias=True))))
                    )
    clean_data = clean_nulls_and_keys(json.loads(new_oas.model_dump_json()))
    return clean_data

def read_oas(file_path:str)->OpenAPI:
    with open(file_path, "r") as file:
        d = yaml.safe_load(file)
    return OpenAPI.model_validate(d)

if __name__ == '__main__':
     oas_path =  '/Users/naamazwerdling/Documents/OASB/policy_validation/airline/openapi.yaml'
     oas = read_oas(oas_path)
     op_oas = op_only_oas(oas, "book_reservation")
     print(op_oas.model_dump_json(indent=2, exclude_none=True, by_alias=True))