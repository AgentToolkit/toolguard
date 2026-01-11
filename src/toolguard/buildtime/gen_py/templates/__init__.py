from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from toolguard.buildtime.utils.py import path_to_module
from toolguard.buildtime.utils.str import to_snake_case

TEMPLATES_DIR = Path(__file__).parent

env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(),
)
env.globals["path_to_module"] = path_to_module
env.globals["to_snake_case"] = to_snake_case


def load_template(template_name: str):
    return env.get_template(template_name)
