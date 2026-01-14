import re


def to_camel_case(txt: str) -> str:
    return (
        txt.replace("_", " ")
        .title()
        .replace(" ", "")
        .replace("-", "_")
        .replace("'", "_")
        .replace(",", "_")
        .replace("’", "_")
        .replace("%", "_")
        .replace("$", "_")
        .replace("#", "_")
        .replace("#@", "_")
    )


def to_snake_case(txt: str) -> str:
    return (
        txt.lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("'", "_")
        .replace(",", "_")
        .replace("’", "_")
        .replace("%", "_")
        .replace("$", "_")
        .replace("#", "_")
        .replace("#@", "_")
    )


def to_pascal_case(name: str) -> str:
    # Split by underscores first
    parts = name.split("_")

    result_parts = []
    for part in parts:
        # Split camelCase or mixedCase segments into words
        subparts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", part)
        # Capitalize each segment
        cap = "".join(s[0].upper() + s[1:] if s else "" for s in subparts)
        result_parts.append(cap)

    return "".join(result_parts)
