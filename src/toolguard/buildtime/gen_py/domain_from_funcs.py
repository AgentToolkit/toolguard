import inspect
import textwrap
import types
from collections import defaultdict, deque
from dataclasses import is_dataclass
from enum import Enum
from pathlib import Path
from types import UnionType
from typing import (
    Annotated,
    Any,
    Callable,
    DefaultDict,
    Dict,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from toolguard.buildtime.utils import py
from toolguard.buildtime.utils.py import module_to_path
from toolguard.runtime.data_types import FileTwin, RuntimeDomain

Dependencies = DefaultDict[type, Set[type]]


def generate_domain_from_functions(
    py_path: Path, app_name: str, funcs: List[Callable], include_module_roots: List[str]
) -> RuntimeDomain:
    # APP init and Types
    (py_path / py.to_py_module_name(app_name)).mkdir(parents=True, exist_ok=True)
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
        app_name=py.to_py_module_name(app_name),
        app_types=types,
        app_api_class_name=api_cls_name,
        app_api=api,
        app_api_impl_class_name=impl_class_name,
        app_api_impl=impl,
        app_api_size=len(funcs),
    )


class APIExtractor:
    def __init__(self, py_path: Path, include_module_roots: List[str] | None = None):
        self.py_path = py_path
        self.include_module_roots = (
            include_module_roots if include_module_roots is not None else []
        )

    def extract_from_functions(
        self,
        funcs: List[Callable],
        interface_name: str,
        interface_module_name: str,
        types_module_name: str,
        impl_module_name: str,
        impl_class_name: str,
    ) -> Tuple[FileTwin, FileTwin, FileTwin]:
        assert all([_is_global_or_class_function(func) for func in funcs])

        self.py_path.mkdir(parents=True, exist_ok=True)

        # used types
        types = FileTwin(
            file_name=module_to_path(types_module_name),
            content=self._generate_types_file(
                *self._collect_all_types_from_functions(funcs)
            ),
        ).save(self.py_path)

        # API interface
        interface = FileTwin(
            file_name=module_to_path(interface_module_name),
            content=self._generate_interface_from_functions(
                funcs, interface_name, types_module_name
            ),
        ).save(self.py_path)

        # API impl interface
        impl = FileTwin(
            file_name=module_to_path(impl_module_name),
            content=self._generate_impl_from_functions(
                funcs,
                impl_class_name,
                interface_module_name,
                interface_name,
                types_module_name,
            ),
        ).save(self.py_path)

        return interface, types, impl

    def extract_from_class(
        self,
        typ: type,
        *,
        interface_name: Optional[str] = None,
        interface_module_name: Optional[str] = None,
        types_module_name: Optional[str] = None,
    ) -> Tuple[FileTwin, FileTwin]:
        """Extract interface and types from a class and save to files."""
        class_name = _get_type_name(typ)
        interface_name = interface_name or "I_" + class_name
        interface_module_name = interface_module_name or f"I_{class_name}".lower()
        types_module_name = types_module_name or f"{class_name}_types".lower()

        self.py_path.mkdir(parents=True, exist_ok=True)

        # Types
        collected, dependencies = self._collect_all_types_from_class(typ)
        types_content = self._generate_types_file(collected, dependencies)
        types_file = module_to_path(types_module_name)
        types = FileTwin(file_name=types_file, content=types_content).save(self.py_path)

        # API interface
        if_content = self._generate_interface_from_class(
            typ, interface_name, types_module_name
        )
        if_file = module_to_path(interface_module_name)
        interface = FileTwin(file_name=if_file, content=if_content).save(self.py_path)

        return interface, types

    def _generate_interface_from_class(
        self, typ: type, interface_name: str, types_module: str
    ) -> str:
        """Generate interface from a class."""
        # Get all methods
        methods = []
        for name, method in inspect.getmembers(typ, predicate=inspect.isfunction):
            if not name.startswith("_"):
                methods.append((name, method))

        # Add class docstring if available
        class_doc = typ.__doc__.strip() if typ.__doc__ else None

        return self._generate_interface(
            methods=[(name, method) for name, method in methods],
            interface_name=interface_name,
            types_module=types_module,
            class_docstring=class_doc,
            use_textwrap=True,
        )

    def _generate_interface_from_functions(
        self, funcs: List[Callable], interface_name: str, types_module: str
    ) -> str:
        """Generate interface from functions."""
        methods = [(_get_type_name(func), func) for func in funcs]
        return self._generate_interface(
            methods=methods,
            interface_name=interface_name,
            types_module=types_module,
            class_docstring=None,
            use_textwrap=False,
        )

    def _generate_interface(
        self,
        methods: List[Tuple[str, Callable]],
        interface_name: str,
        types_module: str,
        class_docstring: Optional[str],
        use_textwrap: bool,
    ) -> str:
        """Common interface generation logic."""
        lines = [
            "# Auto-generated class interface",
            "from typing import *  # type: ignore",
            "from abc import ABC, abstractmethod",
            f"from {types_module} import *",
            "",
            f"class {interface_name}(ABC):",
        ]

        # Add class docstring if available
        if class_docstring:
            lines.append('    """')
            for line in class_docstring.split("\n"):
                lines.append(f"    {line.strip()}")
            lines.append('    """')
        else:
            lines.append("")

        indent = " " * 4
        if not methods:
            lines.append(f"{indent}pass")
        else:
            for method_name, method in methods:
                lines.append(f"{indent}@abstractmethod")
                method_lines = self._get_function_with_docstring(method, method_name)
                lines.extend([line if line else "" for line in method_lines])
                lines.append(f"{indent}{indent}...")
                lines.append("")

        self._add_decimal_import_if_needed(lines)
        result = "\n".join(lines)
        return textwrap.dedent(result) if use_textwrap else result

    def _generate_impl_from_functions(
        self,
        funcs: List[Callable],
        class_name: str,
        interface_module_name: str,
        interface_name: str,
        types_module: str,
    ) -> str:
        lines = [
            "# Auto-generated class",
            "from typing import *",
            "from abc import ABC, abstractmethod",
            f"from {interface_module_name} import {interface_name}",
            f"from {types_module} import *",
            "",
            """class IToolInvoker(ABC):
    T = TypeVar("T")
    @abstractmethod
    async def invoke(self, toolname: str, arguments: Dict[str, Any], model: Type[T])->T:
        ...""",
            "",
        ]

        lines.append(f"class {class_name}({interface_name}):")  # class
        lines.append("")
        lines.append("""    def __init__(self, delegate: IToolInvoker):
        self._delegate = delegate
    """)

        if not funcs:
            lines.append("    pass")
        else:
            for func in funcs:
                # Add method docstring and signature
                method_lines = self._get_function_with_docstring(
                    func, _get_type_name(func)
                )
                lines.extend([line if line else "" for line in method_lines])
                lines.extend(self._generate_delegate_code(func))
                lines.append("")

        self._add_decimal_import_if_needed(lines)
        return "\n".join(lines)

    def _generate_delegate_code(self, func: Callable) -> List[str]:
        func_name = _get_type_name(func)
        indent = " " * 4 * 2
        sig = inspect.signature(func)
        ret = sig.return_annotation
        if ret is inspect._empty:
            ret_name = "None"
        elif hasattr(ret, "__name__"):
            ret_name = ret.__name__
        else:
            ret_name = str(ret)
        return [
            indent + "args = locals().copy()",
            indent + "args.pop('self', None)",
            indent
            + f"return await self._delegate.invoke('{func_name}', args, {ret_name})",
        ]

    def _get_function_with_docstring(
        self, func: Callable[..., Any], func_name: str
    ) -> List[str]:
        """Extract method signature with type hints and docstring."""
        lines = []

        # Get method signature
        method_signature = self._get_method_signature(func, func_name)
        lines.append(f"    {method_signature}:")

        # Add method docstring if available
        if func.__doc__:
            docstring = func.__doc__
            indent = " " * 8
            if docstring:
                lines.append(indent + '"""')
                lines.extend(docstring.strip("\n").split("\n"))
                lines.append(indent + '"""')

        return lines

    def _add_decimal_import_if_needed(self, lines: List[str]) -> None:
        """Add Decimal import if needed in the code."""
        if any("Decimal" in line for line in lines):
            lines.insert(2, "from decimal import Decimal")

    def should_include_type(self, typ: type) -> bool:
        if hasattr(typ, "__module__"):
            module_root = typ.__module__.split(".")[0]
            if module_root in self.include_module_roots:
                return True
        return any([self.should_include_type(arg) for arg in get_args(typ)])

    def _generate_class_definition(self, typ: type) -> List[str]:
        """Generate a class definition with its fields."""
        lines = []
        class_name = _get_type_name(typ)

        if is_dataclass(typ):
            lines.append("@dataclass")

        # Determine base classes
        bases = [_get_type_name(b) for b in _get_type_bases(typ)]
        inheritance = f"({', '.join(bases)})" if bases else ""
        lines.append(f"class {class_name}{inheritance}:")

        indent = " " * 4
        # Add class docstring if available
        if typ.__doc__:
            docstring = typ.__doc__
            if docstring:
                lines.append(f'{indent}"""')
                lines.extend(
                    [f"{indent}{line}" for line in docstring.strip("\n").split("\n")]
                )
                lines.append(f'{indent}"""')

        # Fields
        annotations = getattr(typ, "__annotations__", {})
        if annotations:
            field_descriptions = self._extract_field_descriptions(typ)
            for field_name, field_type in annotations.items():
                if field_name.startswith("_"):
                    continue

                # Handle optional field detection by default=None
                is_optional = False
                default_val = getattr(typ, field_name, ...)
                if default_val is None:
                    is_optional = True
                elif hasattr(typ, "__fields__"):
                    # Pydantic field with default=None
                    field_info = typ.__fields__.get(field_name)
                    if field_info and field_info.is_required() is False:
                        is_optional = True

                type_str = self._format_type(field_type)

                # Avoid wrapping Optional twice
                if is_optional:
                    origin = get_origin(field_type)
                    args = get_args(field_type)
                    already_optional = (
                        origin is Union
                        and type(None) in args
                        or type_str.startswith("Optional[")
                    )
                    if not already_optional:
                        type_str = f"Optional[{type_str}]"

                # Check if we have a description for this field
                description = field_descriptions.get(field_name)
                if description:
                    # Add description as comment for non-Pydantic classes
                    lines.append(f"{indent}{field_name}: {type_str}  # {description}")
                else:
                    # No description available
                    lines.append(f"{indent}{field_name}: {type_str}")

        # Enum
        elif issubclass(typ, Enum):
            if issubclass(typ, str):
                lines.extend(
                    [f'{indent}{entry.name} = "{entry.value}"' for entry in typ]
                )
            else:
                lines.extend([f"{indent}{entry.name} = {entry.value}" for entry in typ])

        else:
            lines.append(f"{indent}pass")

        return lines

    def _extract_field_descriptions(self, typ: type) -> Dict[str, str]:
        """Extract field descriptions from various sources."""
        descriptions = {}

        # Extract from Pydantic models (v1 and v2)
        descriptions.update(self._extract_pydantic_descriptions(typ))

        # Extract from source code comments
        descriptions.update(self._extract_source_comments(typ))

        # Extract from dataclass metadata
        if hasattr(typ, "__dataclass_fields__"):
            for field_name, field in typ.__dataclass_fields__.items():
                if hasattr(field, "metadata") and "description" in field.metadata:
                    if field_name not in descriptions:
                        descriptions[field_name] = field.metadata["description"]

        return descriptions

    def _extract_pydantic_descriptions(self, typ: type) -> Dict[str, str]:
        """Extract descriptions from Pydantic models (v1 and v2)."""
        descriptions = {}

        # Pydantic v1
        if hasattr(typ, "__fields__"):
            for field_name, field_info in typ.__fields__.items():  # type: ignore
                desc = None
                if hasattr(field_info, "field_info") and hasattr(
                    field_info.field_info, "description"
                ):
                    desc = field_info.field_info.description
                elif hasattr(field_info, "description"):
                    desc = field_info.description
                if desc:
                    descriptions[field_name] = desc

        # Pydantic v2
        if hasattr(typ, "model_fields"):
            for field_name, field_info in typ.model_fields.items():  # type: ignore
                if hasattr(field_info, "description") and field_info.description:
                    descriptions[field_name] = field_info.description

        # Check class attributes for Field() definitions
        for attr_name in dir(typ):
            if not attr_name.startswith("_") and attr_name not in descriptions:
                try:
                    attr_value = getattr(typ, attr_name)
                    if hasattr(attr_value, "description") and attr_value.description:
                        descriptions[attr_name] = attr_value.description
                    elif hasattr(attr_value, "field_info") and hasattr(
                        attr_value.field_info, "description"
                    ):
                        descriptions[attr_name] = attr_value.field_info.description
                except Exception:
                    pass

        return descriptions

    def _extract_source_comments(self, typ: type) -> Dict[str, str]:
        """Extract field descriptions from inline comments in source code."""
        descriptions = {}
        try:
            source_lines = inspect.getsourcelines(typ)[0]
            current_field = None

            for line in source_lines:
                line = line.strip()

                # Look for field definitions with type hints
                if ":" in line and not line.startswith(("def ", "class ")):
                    field_part = line.split(":")[0].strip()
                    if " " not in field_part and field_part.isidentifier():
                        current_field = field_part

                # Look for comments
                if "#" in line and current_field:
                    comment = line.split("#", 1)[1].strip()
                    if comment:
                        descriptions[current_field] = comment
                    current_field = None
        except Exception:
            pass

        return descriptions

    def _get_method_signature(self, method: Callable[..., Any], method_name: str):
        """Extract method signature with type hints."""
        try:
            sig = inspect.signature(method)
            # Get param hints
            try:
                param_hints = get_type_hints(method)
            except Exception:
                param_hints = {}

            params = []
            if not sig.parameters.get("self"):
                params.append("self")

            for param_name, param in sig.parameters.items():
                param_str = param_name

                # Add type annotation if available
                if param_name in param_hints:
                    type_str = self._format_type(param_hints[param_name])
                    param_str += f": {type_str}"
                elif param.annotation != param.empty:
                    param_str += f": {param.annotation}"

                # Add default value if present
                if param.default != param.empty:
                    if isinstance(param.default, str):
                        param_str += f' = "{param.default}"'
                    else:
                        param_str += f" = {repr(param.default)}"

                params.append(param_str)

            # Handle return type
            return_annotation = ""
            if "return" in param_hints:
                if param_hints["return"] is not type(None):
                    return_type = self._format_type(param_hints["return"])
                    return_annotation = f" -> {return_type}"
            elif sig.return_annotation != sig.empty:
                return_annotation = f" -> {sig.return_annotation}"

            params_str = ", ".join(params)
            return f"async def {method_name}({params_str}){return_annotation}"

        except Exception:
            # Fallback for problematic signatures
            return f"async def {method_name}(self, *args, **kwargs)"

    def _collect_all_types_from_functions(
        self, funcs: List[Callable]
    ) -> Tuple[Set[type], Dependencies]:
        """Collect all types from function signatures."""
        visited: Set[type] = set()
        collected: Set[type] = set()
        dependencies: Dependencies = defaultdict(set)

        for func in funcs:
            for param, hint in get_type_hints(func).items():  # noqa: B007
                self._collect_types_recursive(hint, visited, collected, dependencies)

        return collected, dependencies

    def _collect_all_types_from_class(
        self, typ: type
    ) -> Tuple[Set[type], Dependencies]:
        """Collect all types used in the class recursively."""
        visited: Set[type] = set()
        collected: Set[type] = set()
        dependencies: Dependencies = defaultdict(set)

        # Field types
        try:
            class_hints = get_type_hints(typ)
            for field, hint in class_hints.items():  # noqa: B007
                self._collect_types_recursive(hint, visited, collected, dependencies)
        except Exception:
            pass

        # Methods and param types
        for name, method in inspect.getmembers(typ, predicate=inspect.isfunction):  # noqa: B007
            try:
                method_hints = get_type_hints(method)
                for hint in method_hints.values():
                    self._collect_types_recursive(
                        hint, visited, collected, dependencies
                    )
            except Exception:
                pass

        # Base class types
        for base in _get_type_bases(typ):
            self._collect_types_recursive(base, visited, collected, dependencies)

        return collected, dependencies

    def _collect_types_recursive(
        self, typ: type, visited: Set[type], acc: Set[type], dependencies: Dependencies
    ):
        """Recursively collect all types from a type hint."""
        visited.add(typ)

        if not self.should_include_type(typ):
            return

        acc.add(typ)
        origin = get_origin(typ)
        args = get_args(typ)

        # Type with generic arguments. eg: List[Person]
        if origin and args:
            for f_arg in args:
                self._collect_types_recursive(f_arg, visited, acc, dependencies)
                # Inline dependency tracking
                if _get_type_name(typ) != _get_type_name(f_arg):
                    dependencies[typ].add(f_arg)
                for arg in get_args(f_arg):
                    dependencies[typ].add(arg)
            return

        # If it's a custom class, try to get its type hints
        try:
            field_hints = typ.__annotations__  # direct fields
            for field_name, field_hint in field_hints.items():  # noqa: B007
                f_origin = get_origin(field_hint)
                if f_origin:
                    for f_arg in get_args(field_hint):
                        self._collect_types_recursive(f_arg, visited, acc, dependencies)
                        # Inline dependency tracking
                        if _get_type_name(typ) != _get_type_name(f_arg):
                            dependencies[typ].add(f_arg)
                        for arg in get_args(f_arg):
                            dependencies[typ].add(arg)
                else:
                    self._collect_types_recursive(
                        field_hint, visited, acc, dependencies
                    )
                    # Inline dependency tracking
                    if _get_type_name(typ) != _get_type_name(field_hint):
                        dependencies[typ].add(field_hint)
                    for arg in get_args(field_hint):
                        dependencies[typ].add(arg)

            for base in _get_type_bases(typ):  # Base classes
                self._collect_types_recursive(base, visited, acc, dependencies)
                # Inline dependency tracking
                if _get_type_name(typ) != _get_type_name(base):
                    dependencies[typ].add(base)
                for arg in get_args(base):
                    dependencies[typ].add(arg)
        except Exception:
            pass

    def _topological_sort_types(self, types: List[type], dependencies: Dependencies):
        """Sort types by their dependencies using topological sort."""
        # Create a mapping of type names to types for easier lookup
        type_map = {_get_type_name(t): t for t in types}

        # Build adjacency list and in-degree count
        adj_list = defaultdict(list)
        in_degree = defaultdict(int)

        # Initialize in-degree for all types
        for t in types:
            type_name = _get_type_name(t)
            if type_name not in in_degree:
                in_degree[type_name] = 0

        # Build the dependency graph
        for dependent_type in types:
            dependent_name = _get_type_name(dependent_type)
            for dependency_type in dependencies.get(dependent_type, set()):
                dependency_name = _get_type_name(dependency_type)
                if (
                    dependency_name in type_map
                ):  # Only consider types we're actually processing
                    adj_list[dependency_name].append(dependent_name)
                    in_degree[dependent_name] += 1

        # Kahn's algorithm for topological sorting
        queue = deque([name for name in in_degree if in_degree[name] == 0])
        result = []

        while queue:
            current = queue.popleft()
            result.append(type_map[current])

            for neighbor in adj_list[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # If we couldn't sort all types, there might be circular dependencies
        # Add remaining types at the end
        sorted_names = {_get_type_name(t) for t in result}
        remaining = [t for t in types if _get_type_name(t) not in sorted_names]
        result.extend(remaining)

        return result

    def _generate_types_file(
        self, collected_types: Set[type], dependencies: Dependencies
    ) -> str:
        """Generate the types file content."""
        lines = []
        lines.append("# Auto-generated type definitions")
        lines.append("from datetime import date, datetime")
        lines.append("from enum import Enum")
        lines.append("from typing import *")
        lines.append("from pydantic import BaseModel, Field")
        lines.append("from dataclasses import dataclass")
        lines.append("")

        custom_classes = []
        for typ in collected_types:
            # Check if it's a class with attributes
            if hasattr(typ, "__annotations__") or (
                hasattr(typ, "__dict__")
                and any(
                    not callable(getattr(typ, attr, None))
                    for attr in dir(typ)
                    if not attr.startswith("_")
                )
            ):
                custom_classes.append(typ)
        custom_classes = self._topological_sort_types(custom_classes, dependencies)

        # Generate custom classes (sorted by dependency)
        for cls in custom_classes:
            class_def = self._generate_class_definition(cls)
            if class_def:  # Only add non-empty class definitions
                lines.extend(class_def)
                lines.append("")

        self._add_decimal_import_if_needed(lines)
        return "\n".join(lines)

    def _format_type(self, typ: type) -> str:
        """Format a type annotation as a string."""
        if typ is None:
            return "Any"

        # Unwrap Annotated[T, ...]
        origin = get_origin(typ)
        if origin is Annotated:
            typ = get_args(typ)[0]
            origin = get_origin(typ)

        # Literal types
        if origin is Literal:
            args = get_args(typ)
            literals = ", ".join(repr(a) for a in args)
            return f"Literal[{literals}]"

        # Union types (including Optional)
        if origin is Union:
            args = get_args(typ)
            non_none = [a for a in args if a is not type(None)]
            if len(non_none) == 1:
                return f"Optional[{self._format_type(non_none[0])}]"
            inner = ", ".join(self._format_type(a) for a in args)
            return f"Union[{inner}]"

        # UnionType (Python 3.10+ syntax: X | Y)
        if origin is UnionType:
            args = get_args(typ)
            return " | ".join(self._format_type(a) for a in args)

        # Generic containers (List, Dict, etc.)
        if origin:
            args = get_args(typ)
            if args:
                inner = ", ".join(self._format_type(a) for a in args)
                return f"{_get_type_name(origin)}[{inner}]"
            return _get_type_name(origin)

        # Simple type
        return _get_type_name(typ)


def _get_type_name(typ) -> str:
    """Get a consistent name for a type object."""
    if hasattr(typ, "__name__"):
        return typ.__name__
    return str(typ)


def _get_type_bases(typ: type) -> List[type]:
    if hasattr(typ, "__bases__"):
        return typ.__bases__  # type: ignore
    return []


def _is_global_or_class_function(func):
    if not callable(func):
        return False

    # Reject lambdas
    if _get_type_name(func) == "<lambda>":
        return False

    # Static methods and global functions are of type FunctionType
    if isinstance(func, types.FunctionType):
        return True

    # Class methods are MethodType but have __self__ as the class, not instance
    if isinstance(func, types.MethodType):
        if inspect.isclass(func.__self__):
            return True  # classmethod
        else:
            return False  # instance method

    return False
