from typing import Dict, List, Any, Optional, re
import os
import re
from difflib import get_close_matches
import json
from typing import List, Optional


class Policy:
	def __init__(self, name: str, description: str, references: List[str],
				 violating_examples: Optional[List[str]] = None, compliance_examples: Optional[List[str]] = None):
		self.name = name
		self.description = description
		self.references = references
		self.violating_examples = violating_examples or []
		self.compliance_examples = compliance_examples or []
	
	def __repr__(self):
		return (f"Policy(name={self.name}, description={self.description}, "
				f"references={self.references}, violating_examples={self.violating_examples}, "
				f"compliance_examples={self.compliance_examples})")


class Policies:
	def __init__(self, policies_json: str):
		self.policies = self._parse_policies(policies_json)
	
	def _parse_policies(self, policies_json: str) -> List[Policy]:
		try:
			data = json.loads(policies_json)
			policies_list = data.get("policies", [])
			
			if isinstance(policies_list, str) and "no relevant policies" in policies_list.lower():
				return []
			
			return [
				Policy(
					name=policy["policy_name"],
					description=policy["description"],
					references=policy["references"],
					violating_examples=policy.get("violating_examples"),
					compliance_examples=policy.get("compliance_examples")
				)
				for policy in policies_list
			]
		except (json.JSONDecodeError, KeyError) as e:
			print(f"Error parsing policies JSON: {e}")
			return []
	
	def __repr__(self):
		return f"Policies({self.policies})"


class TPTDState(Dict[str, Any]):
	policy_text: str
	tools: List[str]
	target_tool: str
	target_tool_description: Dict
	TPTD: Optional[Dict]
	reference_mismatch: List[str]
	review_comments: Optional[str]
	review_score: Optional[int]
	iteration: int
	next_step: str
	outdir: str
	policy_name: Optional[str]
	policy_num: Optional[int]



def read_prompt_file(filename: str) -> str:
	with open(os.path.join(os.path.dirname(__file__), "prompts", filename), "r") as f:
		return f.read()


def generate_messages(system_prompt: str, user_content: str) -> List[Dict[str, str]]:
	return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]


def save_output(outdir: str, filename: str, content: Any):
	with open(os.path.join(outdir, filename), "w") as outfile:
		json.dump(content, outfile, indent=4)

def have_reference_to_fix(state: TPTDState) -> bool:
	if len(state.get("reference_mismatch", {})) > 0 :
		return True
	return False

def reviewer_should_stop(state: TPTDState) -> bool:
	if state.get("review_score", {}).get("score", 0) == 5:
		state.update({"iteration": 0})
		return True
	return False


def fixer_should_stop(state: TPTDState) -> bool:
	if state["iteration"] >= 3:
		state.update({"iteration": 0})
		return True
	return False







def normalize_text(text):
	"""Normalize text by removing punctuation, converting to lowercase, and standardizing spaces."""
	return re.sub(r'\s+', ' ', re.sub(r'[^a-zA-Z0-9\s]', '', text)).strip().lower()


def find_mismatched_references(policy_text, policy_json):
	"""Identify references in JSON that do not match any text in policy_text and return full policy_json with corrections."""
	corrections = json.loads(json.dumps(policy_json))  # Deep copy to avoid modifying original
	unmatched_policies = []
	if isinstance(corrections["policies"], str):
		return corrections, unmatched_policies
	# Normalize policy text and map to original sentences
	normalized_policy_text = normalize_text(policy_text)
	
	for policy in corrections["policies"]:
		corrected_references = []
		has_unmatched = False
		
		for reference in policy["references"]:
			normalized_ref = normalize_text(reference)
			
			if normalized_ref in normalized_policy_text:
				start_idx = normalized_policy_text.find(normalized_ref)
				end_idx = start_idx + len(normalized_ref)
				corrected_references.append(policy_text[start_idx:end_idx])
			else:
				close_match = get_close_matches(normalized_ref, [normalized_policy_text], n=1, cutoff=0.8)
				if close_match:
					start_idx = normalized_policy_text.find(close_match[0])
					end_idx = start_idx + len(close_match[0])
					corrected_references.append(policy_text[start_idx:end_idx])
				else:
					corrected_references.append(reference)  # Keep original if no close match found
					has_unmatched = True
		
		policy["references"] = corrected_references
		if has_unmatched:
			unmatched_policies.append(policy["policy_name"])
	
	return corrections, unmatched_policies