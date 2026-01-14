import re


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
