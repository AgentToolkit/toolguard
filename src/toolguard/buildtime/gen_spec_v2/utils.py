"""Small shared helpers for talking to the model and writing run artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from toolguard.buildtime.llm import I_TG_LLM


def generate_messages(system_prompt: str, user_content: str) -> List[Dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]


async def ask_json(llm: I_TG_LLM, system_prompt: str, user_content: str) -> Dict:
    """One JSON-returning turn. ``chat_json`` already retries unparseable output."""
    return await llm.chat_json(generate_messages(system_prompt, user_content))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
