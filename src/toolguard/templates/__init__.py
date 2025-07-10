from jinja2 import Environment, PackageLoader, select_autoescape

env = Environment(
    loader=PackageLoader("toolguard", "templates"),
    autoescape=select_autoescape()
)

def load_template(template_name:str):
    return env.get_template(template_name)