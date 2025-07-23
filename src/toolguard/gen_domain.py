import inspect
import os
from pathlib import Path
from typing import Callable, List, Optional, Tuple, Union
from os.path import join

from toolguard.api_extractor import APIExtractor
from toolguard.common.array import find
from toolguard.common.py import path_to_module, unwrap_fn
from toolguard.common.str import to_camel_case, to_snake_case
from toolguard.templates import load_template
from toolguard.py_to_oas import tools_to_openapi
from toolguard.utils.datamodel_codegen import run as dm_codegen
from toolguard.common.open_api import OpenAPI, Operation, Parameter, ParameterIn, PathItem, Reference, RequestBody, Response, JSchema, read_openapi
from toolguard.data_types import FileTwin, RuntimeDomain

RUNTIME_PACKAGE_NAME="rt_toolguard"
RUNTIME_INIT_PY = "__init__.py"
RUNTIME_TYPES_PY = "data_types.py"
RUNTIME_APP_TYPES_PY = "domain_types.py"

RUNTIME_APP_API_PY = "api.py"
RUNTIME_APP_API_IMPL_PY = "api_impl.py"

class APIGenerator():
    py_path: str #root of the Python path
    app_name: str
    include_module_roots: List[str]

    def __init__(self, py_path:str, app_name: str, include_module_roots: List[str]) -> None:
        self.py_path = py_path
        self.app_name = app_name
        self.include_module_roots = include_module_roots

    def generate_domain(self, funcs: List[Callable])->RuntimeDomain:
        #ToolGuard Runtime
        os.makedirs(join(self.py_path, RUNTIME_PACKAGE_NAME), exist_ok=True)
        FileTwin.load_from(
            str(Path(__file__).parent), "runtime.py")\
            .save_as(self.py_path, join(RUNTIME_PACKAGE_NAME, RUNTIME_INIT_PY))
        common = FileTwin.load_from(
            str(Path(__file__).parent), "data_types.py")\
            .save_as(self.py_path, join(RUNTIME_PACKAGE_NAME, RUNTIME_TYPES_PY))

        #APP init and Types
        os.makedirs(join(self.py_path, to_snake_case(self.app_name)), exist_ok=True)
        FileTwin(file_name=join(to_snake_case(self.app_name), "__init__.py"), content="")\
            .save(self.py_path)
        
        extractor = APIExtractor(py_path=self.py_path, include_module_roots = self.include_module_roots)
        api_cls_name = f"I_{self.app_name}"
        impl_cls_name = f"{self.app_name}_impl"
        api, types, impl = extractor.extract_from_functions(funcs, 
            interface_name=api_cls_name,
            interface_module_name=f"i_{self.app_name}", 
            types_module_name=f"{self.app_name}_types", 
            impl_module_name=impl_cls_name)

        return RuntimeDomain(
            toolguard_common = common,
            app_types= types,
            app_api_class_name=api_cls_name,
            app_api= api,
            app_api_impl_class_name=impl_cls_name,
            app_api_impl= impl
        )
