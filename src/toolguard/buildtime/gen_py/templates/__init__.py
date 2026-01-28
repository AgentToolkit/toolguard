from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from toolguard.buildtime.utils.py import path_to_module, to_py_func_name

TEMPLATES_DIR = Path(__file__).parent

env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(),
)
env.globals["path_to_module"] = path_to_module
env.globals["to_py_func_name"] = to_py_func_name


def load_template(template_name: str):
    return env.get_template(template_name)
