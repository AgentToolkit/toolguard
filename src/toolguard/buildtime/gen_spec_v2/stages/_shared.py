"""Helpers every stage needs for talking to the LLM and reading its output.

LLM responses are the one input no stage controls, so every read goes through
a defensive accessor here: a response that is valid JSON but the wrong shape
degrades to a default rather than aborting a whole tool's generation.
"""

from typing import Any, Dict, List, Optional

from toolguard.buildtime.gen_spec_v2.models import (
    PolicyItemV2,
    slugify,
    unique_id,
)


def messages(system: str, user: str) -> List[Dict[str, str]]:
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def dict_list(response: Any, key: str) -> List[Dict[str, Any]]:
    """The list of dicts at ``response[key]``, or ``[]`` for any other shape."""
    if not isinstance(response, dict):
        return []
    raw = response.get(key)
    if not isinstance(raw, list):
        return []
    return [entry for entry in raw if isinstance(entry, dict)]


def str_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [v for v in value if isinstance(v, str) and v.strip()]


def item_summary(item: PolicyItemV2) -> Dict[str, Any]:
    """The item as the prompts show it — id, name, description, references."""
    return {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "references": list(item.references),
    }


def build_item(
    raw: Dict[str, Any], tool_name: str, taken: set
) -> Optional[PolicyItemV2]:
    """Build one item from a raw create/expand entry, or ``None`` to drop it.

    Dropped when unnamed, or when it quotes nothing: an item with no reference
    is not grounded in the policy document, and there is no way to check later
    whether it was invented.

    The id is always assigned here, never taken from the model: it must be
    unique within the tool and well-formed, since it is the handle conflicts
    and pending gaps refer to.
    """
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        return None

    references = str_list(raw.get("references"))
    if not references:
        return None

    slug = raw.get("slug") or ""
    if not isinstance(slug, str) or not slug.strip():
        # Some models answer with a fully-qualified id instead of a slug.
        raw_id = raw.get("id")
        slug = raw_id.split(".", 1)[-1] if isinstance(raw_id, str) else ""
    slug = slugify(slug) or slugify(name)

    item_id = unique_id(tool_name, slug, taken)
    taken.add(item_id)

    description = raw.get("description")
    return PolicyItemV2(
        id=item_id,
        name=name.strip(),
        description=description if isinstance(description, str) else "",
        references=references,
    )
