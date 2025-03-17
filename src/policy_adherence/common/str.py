def to_camel_case(snake_str: str) -> str:
    return snake_str.replace("_", " ").title().replace(" ", "")