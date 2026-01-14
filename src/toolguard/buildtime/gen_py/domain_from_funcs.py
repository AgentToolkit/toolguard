import os
from pathlib import Path
from typing import Callable, List
from os.path import join

from toolguard.runtime.data_types import FileTwin, RuntimeDomain
from toolguard.buildtime.utils import py
from toolguard.buildtime.gen_py.api_extractor import APIExtractor


def generate_domain_from_functions(
    py_path: Path, app_name: str, funcs: List[Callable], include_module_roots: List[str]
) -> RuntimeDomain:
    # APP init and Types
    os.makedirs(join(py_path, py.to_py_module_name(app_name)), exist_ok=True)
    FileTwin(
        file_name=Path(py.to_py_module_name(app_name)) / "__init__.py", content=""
    ).save(py_path)

    extractor = APIExtractor(py_path=py_path, include_module_roots=include_module_roots)
    api_cls_name = py.to_py_class_name(f"I_{app_name}")
    impl_module_name = py.to_py_module_name(f"{app_name}.{app_name}_impl")
    impl_class_name = py.to_py_class_name(f"{app_name}_Impl")
    api, types, impl = extractor.extract_from_functions(
        funcs,
        interface_name=api_cls_name,
        interface_module_name=py.to_py_module_name(f"{app_name}.i_{app_name}"),
        types_module_name=py.to_py_module_name(f"{app_name}.{app_name}_types"),
        impl_module_name=impl_module_name,
        impl_class_name=impl_class_name,
    )

    return RuntimeDomain(
        app_name=app_name,
        # toolguard_common=common,
        app_types=types,
        app_api_class_name=api_cls_name,
        app_api=api,
        app_api_impl_class_name=impl_class_name,
        app_api_impl=impl,
        app_api_size=len(funcs),
    )
