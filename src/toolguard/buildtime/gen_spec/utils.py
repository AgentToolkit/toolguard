from functools import cache
from pathlib import Path
from typing import Dict
import os

from typing import List
from pydantic import BaseModel
from toolguard.runtime.data_types import ToolGuardSpec

RETURN_JSON_SUFFIX = """
CRITICAL OUTPUT RULES:
- Output MUST be valid JSON.
- Output MUST match the schema exactly.
- Do NOT include explanations, markdown, comments, or extra text.
- Do NOT wrap the JSON in code fences.
- The first character of the response must be '{' and the last must be '}'.
"""


@cache
def read_prompt_file(filename: str, return_json: bool = True) -> str:
    with open(
        os.path.join(os.path.dirname(__file__), "prompts", filename + ".txt"), "r"
    ) as f:
        prompt = f.read()

    if return_json:
        return prompt + RETURN_JSON_SUFFIX

    return prompt


def generate_messages(system_prompt: str, user_content: str) -> List[Dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]


def save_output(outdir: Path, filename: str | Path, obj: BaseModel):
    path = outdir / filename
    path.write_text(obj.model_dump_json(indent=2), encoding="utf-8")


def normalize_text(text):
    """Normalize text by removing punctuation, converting to lowercase, and standardizing spaces."""
    # return re.sub(r'\s+', ' ', re.sub(r'[^a-zA-Z0-9\s]', '', text)).strip().lower()
    return text.lower()


def split_reference_if_both_parts_exist(reference, policy_text):
    words = reference.split()
    for split_point in range(1, len(words)):
        part1 = " ".join(words[:split_point])
        part2 = " ".join(words[split_point:])

        normalized_part1 = normalize_text(part1)
        normalized_part2 = normalize_text(part2)
        normalized_policy_text = normalize_text(policy_text)

        if (
            normalized_part1 in normalized_policy_text
            and normalized_part2 in normalized_policy_text
        ):
            start_idx1 = normalized_policy_text.find(normalized_part1)
            end_idx1 = start_idx1 + len(part1)
            start_idx2 = normalized_policy_text.find(normalized_part2)
            end_idx2 = start_idx2 + len(part2)
            return [policy_text[start_idx1:end_idx1], policy_text[start_idx2:end_idx2]]
    return None


def find_mismatched_references(policy_text: str, spec: ToolGuardSpec):
    unmatched_policies = []
    normalized_policy_text = normalize_text(policy_text)

    for item in spec.policy_items:
        corrected_references = []
        has_unmatched = False

        for reference in item.references:
            normalized_ref = normalize_text(reference)
            # if normalized ref in policy doc- just copy the original
            if normalized_ref in normalized_policy_text:
                start_idx = normalized_policy_text.find(normalized_ref)
                end_idx = start_idx + len(reference)
                corrected_references.append(policy_text[start_idx:end_idx])
            else:
                # close_match = get_close_matches(normalized_ref, [normalized_policy_text], n=1, cutoff=0.9)
                # if close_match:
                # 	start_idx = normalized_policy_text.find(close_match[0])
                # 	end_idx = start_idx + len(close_match[0])
                # 	corrected_references.append(policy_text[start_idx:end_idx])
                # else:
                split_segments = split_reference_if_both_parts_exist(
                    reference, policy_text
                )
                if split_segments:
                    corrected_references.extend(split_segments)
                else:
                    corrected_references.append(
                        reference
                    )  # Keep original if no match found
                    has_unmatched = True

        item.references = corrected_references
        if has_unmatched:
            unmatched_policies.append(item.name)

    return spec, unmatched_policies
