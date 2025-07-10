from jinja2 import Environment, PackageLoader, select_autoescape

from toolguard.common.py import py_module

env = Environment(
    loader=PackageLoader("toolguard", "templates"),
    autoescape=select_autoescape(),
)
env.globals["py_module"] = py_module

def load_template(template_name:str):
    return env.get_template(template_name)