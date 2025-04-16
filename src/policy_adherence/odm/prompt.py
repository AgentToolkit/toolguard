

from typing import List
from programmatic_ai import generative

from policy_adherence.types import SourceFile, ToolPolicyItem

model = "gpt-4o-2024-08-06"
@generative(model=model, provider="azure", sdk="litellm")
def improve_tool_rules(prev_impl:SourceFile,  ruleset_src:SourceFile, bom_src:SourceFile, policy_item: ToolPolicyItem, review_comments: List[str])-> str:
    """
    Improve the previous tool-call check rules (in IBM Operational Decision Manager, ODM, Business Rules (Action Rules), BAL syntax) to cover all tool policy-items according to the review-comments.

    Args:
        prev_impl (SourceFile): previous implementation of the rules to check tool-call adherence.
        ruleset_src (SourceFile): The business Ruleset definition, with its input, output and rule.
        bom_src (SourceFile): the input Business Object Model (BOM) with name and JSON schema.
        policy_item (ToolPolicyItem): Requirements for this tool.
        review_comments (List[str]): Review comments on the current implementation. For example, pylint errors or Failed unit-tests.

    Returns:
        str: Improved rules decleration in ODM BAL syntax.

    **Implementation Rules:**"
    - ALL tool policy items must be validated on the tool arguments.
    - The rules should be simple.
    - The rules should be well documented.
    - You should just validate the tool-call. You should never call the tool itself.
    """
    ...