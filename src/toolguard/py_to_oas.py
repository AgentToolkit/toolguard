from typing import Any, Callable, Dict, List, Literal
import docstring_parser
import inspect
import typing
from typing import get_origin, get_args

from pydantic import BaseModel

from toolguard.common.http import MEDIA_TYPE_APP_JSON
from toolguard.common.jschema import JSONSchemaTypes, JSchema
from toolguard.common.open_api import Info, MediaType, OpenAPI, Operation, Parameter, ParameterIn, PathItem, Response, Server
from toolguard.common.py import unwrap_fn

PRIMITIVE_PY_TYPES_TO_JSCHMA_TYPES = {
    str: JSONSchemaTypes.string,
    int: JSONSchemaTypes.integer,
    float: JSONSchemaTypes.number,
    bool: JSONSchemaTypes.boolean
}

def extract_param_docs(fn_doc:str) ->Dict[str, str]:
    parsed = docstring_parser.parse(fn_doc or "")
    return {
        param.arg_name: param.description or "" 
        for param in parsed.params
    }

def py_type_to_json_schema(py_type:Any) -> JSchema:
    origin = get_origin(py_type)
    args = get_args(py_type)

    # Handle optional (Union[X, None])
    if origin is typing.Union and type(None) in args:
        non_none_type = [arg for arg in args if arg is not type(None)][0]
        schema = py_type_to_json_schema(non_none_type)
        schema.nullable = True
        return schema

    # Handle List[X], Tuple[X], etc.
    if origin in (list, typing.List, tuple, typing.Tuple):
        item_type = args[0] if args else typing.Any
        return JSchema( 
            type = JSONSchemaTypes.array,
            items = py_type_to_json_schema(item_type)
        )

    # Handle Dict[str, X]
    if origin in (dict, typing.Dict):
        key_type, val_type = args if args else (str, typing.Any)
        return JSchema(
            type = JSONSchemaTypes.object,
            additionalProperties = py_type_to_json_schema(val_type)
        )

    # Handle base Python types
    if py_type in PRIMITIVE_PY_TYPES_TO_JSCHMA_TYPES:
        return JSchema(type= PRIMITIVE_PY_TYPES_TO_JSCHMA_TYPES.get(py_type))
    if py_type is None or py_type is type(None):
        return JSchema(type = JSONSchemaTypes.null)
    if py_type is typing.Any:
        return JSchema()

    # Handle custom classes with annotations (like dataclasses or tool args)
    if inspect.isclass(py_type) and hasattr(py_type, "__annotations__"):
        props = {}
        required = []
        for name, typ in py_type.__annotations__.items():
            props[name] = py_type_to_json_schema(typ)
            if not typing.get_origin(typ) is typing.Union or type(None) not in typing.get_args(typ):
                required.append(name)

        return JSchema(
            type = JSONSchemaTypes.object,
            properties = props,
            required = required or None
        )

    # Fallback
    return JSchema(type = JSONSchemaTypes.string)

def func_to_oas_operation(func:Callable)->Operation:
    original_fn = unwrap_fn(func)

    sig = inspect.signature(original_fn)
    fn_doc = inspect.getdoc(original_fn) or ""
    param_docs = extract_param_docs(fn_doc)
    
    op_params = []
    for fn_param_name, fn_param in sig.parameters.items():
        if fn_param_name == "self":
            continue
        op_param = Parameter(
            name = fn_param_name,
            description = param_docs.get(fn_param_name),
            **{ #Pylance have trouble with pydantic fields that use alias for Python keywords or names like "in".
                "in": ParameterIn.query,
                "schema": JSchema(
                    type= py_type_to_json_schema(fn_param.annotation).type,
                    default=fn_param.default if fn_param.default != inspect.Parameter.empty else None,
                )
            },
            required = fn_param.default == inspect.Parameter.empty,
        )
        op_params.append(op_param)

    return Operation(
        summary = fn_doc.split('\n')[0],
        description= fn_doc,
        operationId = original_fn.__name__,
        parameters = op_params,
        responses = {"200": Response(
            description= "Successful response",
            content = {
                MEDIA_TYPE_APP_JSON: MediaType(schema=py_type_to_json_schema(sig.return_annotation))
            }
        )},
    )

def tools_to_openapi(title:str, tools: List[Callable]) ->OpenAPI:
    def tool_path(tool:Callable):
        return unwrap_fn(tool).__name__
    
    def tool_method(tool:Callable)->Literal["get", "post"]:
        #FIXME?
        return "post"
    
    return OpenAPI(
        openapi="3.0.3",
        info=Info(
            title=title,
            description=title,
            version="1.0.0"
        ),
        servers=[
            Server(url=":python", description="Python functions")
        ],
        paths={
            tool_path(tool):PathItem(
                **{tool_method(tool): func_to_oas_operation(tool)}
            ) for tool in tools
        }
    )

#----------
if __name__ == "__main__":
    class R(BaseModel):
        a:int
        b:str
        c:'R'

    from langchain.tools import tool
    @tool
    def greet(name: str, title: str = "Mr.") -> R:
        """
        Greet someone with a title.

        Args:
            name: The person's name.
            title: The person's title (default is "Mr.").
        """
        pass

    x= tools_to_openapi("Clinic tools", [greet])
    print(x.model_dump_json(indent=2, exclude_none=True, by_alias=True))