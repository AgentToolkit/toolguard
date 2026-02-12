import asyncio
import json
from pathlib import Path
from typing import Callable, List, Optional, Tuple, cast, Set
from loguru import logger
from pydantic import BaseModel, Field

from toolguard.buildtime.compat.strenum import StrEnum
from toolguard.buildtime.data_types import TOOLS
from toolguard.buildtime.gen_spec.data_types import ToolInfo
from toolguard.buildtime.gen_spec.fn_to_toolinfo import function_to_toolInfo
from toolguard.buildtime.gen_spec.oas_to_toolinfo import openapi_to_toolinfos
from toolguard.buildtime.gen_spec.utils import (
    find_mismatched_references,
    generate_messages,
    read_prompt_file,
    save_output,
)
from toolguard.buildtime.llm import I_TG_LLM
from toolguard.buildtime.utils.open_api import OpenAPI
from toolguard.runtime.data_types import ToolGuardSpec, ToolGuardSpecItem


class PolicySpecStep(StrEnum):
    CREATE_POLICIES = "CREATE_POLICIES"
    ADD_POLICIES = "ADD_POLICIES"
    REVIEW_POLICIES = "REVIEW_POLICIES"
    REVIEW_POLICIES_FEASIBILITY = "REVIEW_POLICIES_FEASIBILITY"
    CORRECT_REFERENCES = "CORRECT_REFERENCES"
    REVIEW_POLICIES_SELF_CONTAINED = "REVIEW_POLICIES_SELF_CONTAINED"


# --- Options container ---
class PolicySpecOptions(BaseModel):
    spec_steps: Set[PolicySpecStep] = Field(
        default_factory=lambda: set(PolicySpecStep),
        description="Set of policy spec steps to run. Defaults to all steps.",
    )
    add_iterations: int = Field(
        default=3, description="Number of iterations for adding policies"
    )
    example_number: Optional[int] = Field(
        default=None,
        description="Number of examples: None = as many as LLM wants, 0 = no examples, >0 = that many",
    )

    def param_description(self) -> str:
        parts = []
        all_steps = set(PolicySpecStep)
        if self.spec_steps != all_steps:
            step_names = ",".join(sorted(step.name for step in self.spec_steps))
            parts.append(f"steps=[{step_names}]")
        else:
            parts.append("steps=ALL")

        # Iterations (only mention if not default)
        if self.add_iterations != 3:
            parts.append(f"add_iter={self.add_iterations}")

        # Examples handling
        if self.example_number is None:
            parts.append("examples=auto")
        elif self.example_number == 0:
            parts.append("examples=none")
        else:
            parts.append(f"examples={self.example_number}")

        return "_".join(parts)


async def extract_toolguard_specs(
    policy_text: str,
    tools: TOOLS,
    step1_output_dir: Path,
    llm: I_TG_LLM,
    tools2guard: Optional[List[str]] = None,  # None==all tools
    options: Optional[PolicySpecOptions] = None,
) -> List[ToolGuardSpec]:
    tool_infos = _tools_to_tool_infos(tools)
    step1_output_dir.mkdir(parents=True, exist_ok=True)
    # Use options if provided, otherwise default behavior (all steps, example_number=None)
    options = options or PolicySpecOptions()
    process_dir = step1_output_dir / "process"
    process_dir.mkdir(parents=True, exist_ok=True)
    generator = ToolGuardSpecGenerator(
        llm, policy_text, tool_infos, process_dir, options
    )

    async def do_one_tool(tool_name: str) -> ToolGuardSpec:
        spec = await generator.generate_policy(tool_name)
        if spec.policy_items:
            save_output(step1_output_dir, tool_name + ".json", spec)
        return spec

    specs = await asyncio.gather(
        *[
            do_one_tool(tool.name)
            for tool in tool_infos
            if ((tools2guard is None) or (tool.name in tools2guard))
        ]
    )
    logger.debug("All tools done")
    return specs


class ToolGuardSpecGenerator:
    def __init__(
        self,
        llm: I_TG_LLM,
        policy_document: str,
        tools: List[ToolInfo],
        out_dir: Path,
        options: Optional[PolicySpecOptions] = None,
    ) -> None:
        self.llm = llm
        self.policy_document = policy_document
        self.tools_descriptions = {tool.name: tool.description for tool in tools}
        self.tools_details = {tool.name: tool for tool in tools}
        self.out_dir = out_dir
        self.options = options or PolicySpecOptions()

    def _effective_steps(self) -> Set[PolicySpecStep]:
        """Return the set of steps that should actually run."""
        return self.options.spec_steps

    def _add_iterations(self) -> int:
        """Return the set of steps that should actually run."""
        return self.options.add_iterations

    def _effective_example_number(self) -> Optional[int]:
        """
        Return number of examples to generate:
        None = let LLM decide,
        0 = no examples,
        int >0 = generate that many examples.
        """
        return self.options.example_number

    async def generate_policy(self, tool_name: str) -> ToolGuardSpec:
        if PolicySpecStep.CREATE_POLICIES in self._effective_steps():
            spec = await self.create_spec(tool_name)
        if PolicySpecStep.ADD_POLICIES in self._effective_steps():
            for i in range(self._add_iterations()):
                await self.add_items(tool_name, spec, i)
            if not spec.policy_items:
                return spec
        if PolicySpecStep.REVIEW_POLICIES in self._effective_steps():
            await self.review_policy(tool_name, spec)

        if PolicySpecStep.CORRECT_REFERENCES in self._effective_steps():
            await self.add_references(tool_name, spec)
            self.reference_correctness(tool_name, spec)

        if PolicySpecStep.REVIEW_POLICIES_SELF_CONTAINED in self._effective_steps():
            await self.ensure_self_contained(tool_name, spec)

        if PolicySpecStep.REVIEW_POLICIES_FEASIBILITY in self._effective_steps():
            await self.review_policy_feasibility(tool_name, spec)

        await self.example_creator(tool_name, spec, self._effective_example_number())
        return spec

    async def create_spec(self, tool_name: str) -> ToolGuardSpec:
        logger.debug(f"create_spec({tool_name})")
        system_prompt = read_prompt_file("create_policy")
        system_prompt = system_prompt.replace("ToolX", tool_name)
        tool = self.tools_details[tool_name]
        user_content = f"""Policy Document: {self.policy_document}
Tools Descriptions: {json.dumps(self.tools_descriptions)}
Target Tool: {tool.model_dump_json(indent=2)}
"""
        spec_dict = await self.llm.chat_json(
            generate_messages(system_prompt, user_content)
        )
        spec = ToolGuardSpec(tool_name=tool_name, **spec_dict)
        save_output(self.out_dir, f"{tool_name}.json", spec)
        return spec

    async def add_items(self, tool_name: str, spec: ToolGuardSpec, iteration: int = 0):
        logger.debug(f"add_policy({tool_name})")
        system_prompt = read_prompt_file("add_policies")
        tool = self.tools_details[tool_name]
        user_content = f"""Policy Document: {self.policy_document}
Tools Descriptions: {json.dumps(self.tools_descriptions)}
Target Tool: {tool.model_dump_json(indent=2)}
spec: {spec.model_dump_json(indent=2)}"""

        response = await self.llm.chat_json(
            generate_messages(system_prompt, user_content)
        )

        item_ds = (
            response["additionalProperties"]["policy_items"]
            if "additionalProperties" in response and "policy_items" not in response
            else response["policy_items"]
        )

        spec.debug["iteration"] = iteration
        for item_d in item_ds:
            spec.policy_items.append(ToolGuardSpecItem.model_validate(item_d))

        save_output(self.out_dir, f"{tool_name}_ADD_{iteration}.json", spec)

    async def split(self, tool_name: str, spec: ToolGuardSpec):
        # todo: consider addition step to split policy by policy and not overall
        logger.debug(f"split({tool_name})")
        tool = self.tools_details[tool_name]
        system_prompt = read_prompt_file("split")
        user_content = f"""Policy Document: {self.policy_document}
Tools Descriptions: {json.dumps(self.tools_descriptions)}
Target Tool: {tool.model_dump_json(indent=2)}
spec: {spec.model_dump_json(indent=2)}"""
        spec_d = await self.llm.chat_json(
            generate_messages(system_prompt, user_content)
        )
        spec.policy_items = [
            ToolGuardSpecItem.model_validate(item_d)
            for item_d in spec_d["policy_items"]
        ]
        save_output(self.out_dir, f"{tool_name}_split.json", spec)

    async def merge(self, tool_name: str, spec: ToolGuardSpec):
        # todo: consider addition step to split policy by policy and not overall
        logger.debug(f"merge({tool_name})")
        system_prompt = read_prompt_file("merge")
        tool = self.tools_details[tool_name]
        user_content = f"""Policy Document: {self.policy_document}
Tools Descriptions: {json.dumps(self.tools_descriptions)}
Target Tool: {tool.model_dump_json(indent=2)}
spec: {spec.model_dump_json(indent=2)}"""
        spec_d = await self.llm.chat_json(
            generate_messages(system_prompt, user_content)
        )
        spec.policy_items = [
            ToolGuardSpecItem.model_validate(item_d)
            for item_d in spec_d["policy_items"]
        ]
        save_output(self.out_dir, f"{tool_name}_merge.json", spec)

    def move2archive(self, reviews) -> Tuple[bool, str]:
        comments = ""
        num = len(reviews)
        if num == 0:
            return False, ""
        counts = {
            "is_relevant": 0,
            "is_tool_specific": 0,
            "can_be_validated": 0,
            # "is_actionable": 0,
        }

        for r in reviews:
            logger.debug(
                f"{r['is_relevant'] if 'is_relevant' in r else ''}\t{r['is_tool_specific'] if 'is_tool_specific' in r else ''}\t{r['can_be_validated'] if 'can_be_validated' in r else ''}\t{r['is_actionable'] if 'is_actionable' in r else ''}\t{r['is_self_contained'] if 'is_self_contained' in r else ''}\t{r['score'] if 'score' in r else ''}\t"
            )

            counts["is_relevant"] += r["is_relevant"] if "is_relevant" in r else 0
            counts["is_tool_specific"] += (
                r["is_tool_specific"] if "is_tool_specific" in r else 0
            )
            counts["can_be_validated"] += (
                r["can_be_validated"] if "can_be_validated" in r else 0
            )
            # counts["is_actionable"] += r["is_actionable"] if "is_actionable" in r else 0

            if not all(
                e in r
                for e in [
                    "is_relevant",
                    "is_tool_specific",
                    "can_be_validated",
                    # "is_actionable",
                ]
            ) or not (
                r["is_relevant"] and r["is_tool_specific"] and r["can_be_validated"]
                # and r["is_actionable"]
            ):
                comments += r["comments"] + "\n"

        return not (all(float(counts[key]) / num > 0.5 for key in counts)), comments

    async def review_policy(self, tool_name: str, spec: ToolGuardSpec):
        logger.debug(f"review_policy({tool_name})")
        # system_prompt = read_prompt_file("policy_reviewer")
        system_prompt = read_prompt_file("review_policy_relevance")
        all_tool_descs = json.dumps(self.tools_descriptions)
        tool_desc = self.tools_descriptions[tool_name]

        async def review_item(item: ToolGuardSpecItem):
            user_content = f"""Policy Document: {self.policy_document}
Tools Descriptions: {all_tool_descs}
Target Tool: {tool_desc}
policy: {item.model_dump_json(indent=2)}"""
            response = await self.llm.chat_json(
                generate_messages(system_prompt, user_content)
            )
            return response

        async def analyze_item(item: ToolGuardSpecItem):
            reviews = await asyncio.gather(*[review_item(item) for i in range(5)])
            archive, comments = self.move2archive(reviews)
            logger.debug(archive)
            if archive:
                if "archive" not in spec.debug:
                    spec.debug["archive"] = []
                item.debug["comments"] = comments
                spec.debug["archive"].append(item)
                spec.policy_items.remove(item)

        await asyncio.gather(*[analyze_item(item) for item in spec.policy_items])

        save_output(self.out_dir, f"{tool_name}_rev.json", spec)

    async def review_policy_feasibility(self, tool_name: str, spec: ToolGuardSpec):
        logger.debug(f"review_policy_feasibility({tool_name})")
        system_prompt = read_prompt_file("review_policy_feasibility")
        all_tool_descs = json.dumps(self.tools_descriptions)
        tool_desc = self.tools_descriptions[tool_name]

        async def review_item_feasibility(item: ToolGuardSpecItem):
            user_content = f"""Policy Document: {self.policy_document}
Tools Descriptions: {all_tool_descs}
Target Tool: {tool_desc}
policy: {item.model_dump_json(indent=2)}"""
            response = await self.llm.chat_json(
                generate_messages(system_prompt, user_content)
            )
            return response

        async def analyze_item_feasibility(item: ToolGuardSpecItem):
            repeat = 3
            reviews = await asyncio.gather(
                *[review_item_feasibility(item) for i in range(repeat)]
            )
            validated_count = 0
            reasons = []
            comments = []
            missing_tool_description = None
            for response in reviews:
                if "can_be_validated" in response:
                    if response["can_be_validated"]:
                        validated_count += 1
                    else:
                        if "rejection_reason" in response:
                            reason = response["rejection_reason"]
                            if reason == "missing_tool":
                                missing_tool_description = response[
                                    "missing_tool_description"
                                ]
                            reasons.append(reason)
                        if "comments" in response:
                            comments.append(response["comments"])

            if validated_count / repeat < 0.5:
                spec.policy_items.remove(item)

                if not hasattr(item, "debug") or item.debug is None:
                    item.debug = {}

                item.debug["feasibility_reasons"] = reasons
                item.debug["missing_tool_description"] = missing_tool_description
                item.debug["feasibility_comments"] = comments

                if "archive" not in spec.debug:
                    spec.debug["archive"] = []
                spec.debug["archive"].append(item)

        items = list(spec.policy_items)
        await asyncio.gather(*[analyze_item_feasibility(item) for item in items])

        save_output(self.out_dir, f"{tool_name}_rev_feasibility.json", spec)

    async def ensure_self_contained(self, tool_name: str, spec: ToolGuardSpec):
        logger.debug(f"self_containe({tool_name})")
        system_prompt = read_prompt_file("policy_reviewer_self_contained")
        tool = self.tools_details[tool_name]

        async def ensure_item_contained(item: ToolGuardSpecItem):
            user_content = f"""Policy Document: {self.policy_document}
Tools Descriptions: {json.dumps(self.tools_descriptions)}
Target Tool: {tool.model_dump_json(indent=2)}
policy: {item.model_dump_json(indent=2)}"""
            response = await self.llm.chat_json(
                generate_messages(system_prompt, user_content)
            )
            if "is_self_contained" in response:
                is_self_contained = response["is_self_contained"]
                if not is_self_contained:
                    if "alternative_description" in response:
                        item.description = response["alternative_description"]
                    else:
                        logger.error(
                            "Error: review is_self_contained is false but no alternative_description."
                        )
            else:
                logger.error("Error: review did not provide is_self_contained.")
            return response

        await asyncio.gather(
            *[ensure_item_contained(item) for item in spec.policy_items]
        )
        save_output(self.out_dir, f"{tool_name}_self_contained.json", spec)

    async def add_references(self, tool_name: str, spec: ToolGuardSpec):
        logger.debug(f"add_ref({tool_name})")
        system_prompt = read_prompt_file("add_references")
        # remove old refs (used to help avoid duplications)
        tool = self.tools_details[tool_name]

        async def add_item_ref(item: ToolGuardSpecItem):
            user_content = f"""Policy Document: {self.policy_document}
Tools Descriptions: {json.dumps(self.tools_descriptions)}
Target Tool: {tool.model_dump_json(indent=2)}
policy: {item.model_dump_json(indent=2)}"""
            response = await self.llm.chat_json(
                generate_messages(system_prompt, user_content)
            )
            if "references" in response:
                item.references = response["references"]
            else:
                logger.error("Error! no references in response")
                logger.error(response)

        await asyncio.gather(*[add_item_ref(item) for item in spec.policy_items])
        save_output(self.out_dir, f"{tool_name}_ref.json", spec)

    def reference_correctness(self, tool_name: str, spec: ToolGuardSpec):
        logger.debug(f"reference_correctness({tool_name})")
        save_output(self.out_dir, f"{tool_name}_ref_orig_.json", spec)
        spec, unmatched_policies = find_mismatched_references(
            self.policy_document, spec
        )
        save_output(self.out_dir, f"{tool_name}_ref_correction_.json", spec)

    async def example_creator(
        self, tool_name: str, spec: ToolGuardSpec, fixed_examples: Optional[int] = None
    ):
        logger.debug(f"example_creator({tool_name})")
        if fixed_examples:
            system_prompt = read_prompt_file("create_short_examples")
            system_prompt = system_prompt.replace("EX_FIX_NUM", str(fixed_examples))
        else:
            system_prompt = read_prompt_file("create_examples")

        system_prompt = system_prompt.replace("ToolX", tool_name)
        tool = self.tools_details[tool_name]

        async def create_item_examples(item: ToolGuardSpecItem):
            user_content = f"""Tools Descriptions: {json.dumps(self.tools_descriptions)}
Target Tool: {tool.model_dump_json(indent=2)}
Policy: {item.model_dump_json(indent=2)}"""

            response = await self.llm.chat_json(
                generate_messages(system_prompt, user_content)
            )
            if "violation_examples" in response:
                item.violation_examples = response["violation_examples"]

            if "compliance_examples" in response:
                item.compliance_examples = response["compliance_examples"]

        await asyncio.gather(
            *[create_item_examples(item) for item in spec.policy_items]
        )
        save_output(self.out_dir, f"{tool_name}_examples.json", spec)


def _tools_to_tool_infos(
    tools: TOOLS,
) -> List[ToolInfo]:
    # case1: an OpenAPI spec dictionary
    if isinstance(tools, dict):
        oas = OpenAPI.model_validate(tools)
        return openapi_to_toolinfos(oas)

    # Case 3: List of functions/ List of methods / List of ToolInfos
    if isinstance(tools, list):
        tools_info = []
        for tool in tools:
            if callable(tool):
                info = function_to_toolInfo(cast(Callable, tool))
                tools_info.append(info)
            else:
                raise NotImplementedError()
        return tools_info

    raise NotImplementedError()
