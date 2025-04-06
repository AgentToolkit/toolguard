def to_camel_case(snake_str: str) -> str:
    return snake_str.replace("_", " ").title().replace(" ", "")

def to_snake_case(human_name: str)->str:
    return human_name.replace(" ", "_")
