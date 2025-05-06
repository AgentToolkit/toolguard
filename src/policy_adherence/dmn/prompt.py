

from typing import List
from programmatic_ai import generative

from policy_adherence.data_types import SourceFile, ToolPolicyItem

model = "gpt-4o-2024-08-06"
@generative(model=model, provider="azure", sdk="litellm")
def improve_tool_rules(prev_impl:SourceFile, policy_item: ToolPolicyItem, review_comments: List[str])-> str:
    """
    Improve the previous tool-call check rules (in DMN, Decision Model and Notation syntax) to cover all tool policy-items according to the review-comments.

    Args:
        prev_impl (SourceFile): previous implementation of the DMN to check tool-call adherence.
        policy_item (ToolPolicyItem): Requirements for this tool.
        review_comments (List[str]): Review comments on the current implementation. For example, pylint errors or Failed unit-tests.

    Returns:
        str: Improved rules decleration in DMN definitions xml syntax.

    **Implementation Rules:**"
    - ALL tool policy items must be validated on the tool arguments.
    - The rules should be simple.
    - The rules should be well documented.
    - You should just validate the tool-call. You should never call the tool itself.
    """
    ...