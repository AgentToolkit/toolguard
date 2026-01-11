import asyncio
import json
import os
from pathlib import Path
from typing import List, Optional, Tuple
from logging import getLogger

from toolguard.runtime.data_types import ToolGuardSpec, ToolGuardSpecItem
from toolguard.buildtime.data_types import ToolInfo
from toolguard.buildtime.llm.i_tg_llm import I_TG_LLM
from toolguard.buildtime.gen_spec.utils import (
    read_prompt_file,
    generate_messages,
    save_output,
    find_mismatched_references,
)

logger = getLogger(__name__)


class ToolGuardSpecGenerator:
    def __init__(
        self, llm: I_TG_LLM, policy_document: str, tools: List[ToolInfo], out_dir: Path
    ) -> None:
        self.llm = llm
        self.policy_document = policy_document
        self.tools_descriptions = {tool.name: tool.description for tool in tools}
        self.tools_details = {tool.name: tool for tool in tools}
        self.out_dir = out_dir

    async def generate_minimal_policy(self, tool_name: str) -> ToolGuardSpec:
        spec = await self.create_spec(tool_name)
        if not spec.policy_items:
            return spec

        await self.example_creator(tool_name, spec, 4)
        return spec

    async def generate_policy(self, tool_name: str) -> ToolGuardSpec:
        spec = await self.create_spec(tool_name)
        for i in range(3):
            await self.add_items(tool_name, spec, i)
        if not spec.policy_items:
            return spec

        await self.split(tool_name, spec)
        if len(spec.policy_items) > 1:
            await self.merge(tool_name, spec)
        await self.review_policy(tool_name, spec)
        await self.add_references(tool_name, spec)
        self.reference_correctness(tool_name, spec)

        await self.example_creator(tool_name, spec)
        for i in range(5):
            await self.add_examples(tool_name, spec, i)
        await self.merge_examples(tool_name, spec)
        # spec = self.fix_examples(tool_name, spec)
        await self.review_examples(tool_name, spec)
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

        spec._debug["iteration"] = iteration
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
            "is_actionable": 0,
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
            counts["is_actionable"] += r["is_actionable"] if "is_actionable" in r else 0

            if not all(
                e in r
                for e in [
                    "is_relevant",
                    "is_tool_specific",
                    "can_be_validated",
                    "is_actionable",
                ]
            ) or not (
                r["is_relevant"]
                and r["is_tool_specific"]
                and r["can_be_validated"]
                and r["is_actionable"]
            ):
                comments += r["comments"] + "\n"

        return not (all(float(counts[key]) / num > 0.5 for key in counts)), comments

    async def review_policy(self, tool_name: str, spec: ToolGuardSpec):
        logger.debug(f"review_policy({tool_name})")
        system_prompt = read_prompt_file("policy_reviewer")
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

        async def analyze_item(item: ToolGuardSpecItem):
            reviews = await asyncio.gather(*[review_item(item) for i in range(5)])
            archive, comments = self.move2archive(reviews)
            logger.debug(archive)
            if archive:
                if "archive" not in spec._debug:
                    spec._debug["archive"] = []
                spec._debug["archive"].append(item)
                spec.policy_items.remove(item)

        await asyncio.gather(*[analyze_item(item) for item in spec.policy_items])

        save_output(self.out_dir, f"{tool_name}_rev.json", spec)

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

    async def add_examples(self, tool_name: str, spec: ToolGuardSpec, iteration: int):
        logger.debug(f"add_examples({tool_name})")
        system_prompt = read_prompt_file("add_examples")
        system_prompt = system_prompt.replace("ToolX", tool_name)
        tool = self.tools_details[tool_name]

        async def add_item_examples(item: ToolGuardSpecItem):
            user_content = f"""Tools Descriptions: {json.dumps(self.tools_descriptions)}
Target Tool: {tool.model_dump_json(indent=2)}
Policy: {item}"""
            response = await self.llm.chat_json(
                generate_messages(system_prompt, user_content)
            )
            if "violation_examples" in response:
                for vexample in response["violation_examples"]:
                    item.violation_examples.append(vexample)
            if "compliance_examples" in response:
                for cexample in response["compliance_examples"]:
                    item.compliance_examples.append(cexample)

        await asyncio.gather(*[add_item_examples(item) for item in spec.policy_items])
        save_output(self.out_dir, f"{tool_name}_ADD_examples{iteration}.json", spec)

    async def merge_examples(self, tool_name: str, spec: ToolGuardSpec):
        logger.debug(f"merge_examples({tool_name})")
        system_prompt = read_prompt_file("merge_examples")
        system_prompt = system_prompt.replace("ToolX", tool_name)
        tool = self.tools_details[tool_name]

        async def merge_item_examples(item: ToolGuardSpecItem):
            user_content = f"""Tools Descriptions: {json.dumps(self.tools_descriptions)}
Target Tool: {tool.model_dump_json(indent=2)}
Policy Name: {item.name}
Policy Description: {item.description}"""
            user_content += f"\n\nViolation Examples: {item.violation_examples}"
            user_content += f"\n\nCompliance Examples: {item.compliance_examples}"
            response = await self.llm.chat_json(
                generate_messages(system_prompt, user_content)
            )
            item.violation_examples = response["violation_examples"]
            item.compliance_examples = response["compliance_examples"]

        await asyncio.gather(*[merge_item_examples(item) for item in spec.policy_items])
        save_output(self.out_dir, f"{tool_name}_merge_examples.json", spec)

    #     async def fix_item_examples(self, tool_name: str, spec: ToolGuardSpec, item: ToolGuardSpecItem):
    #         orig_prompt = read_prompt_file("fix_example")
    #         tool = self.tools_details[tool_name]

    #         for etype in ["violation", "compliance"]:
    #             fixed_examples = []
    #             for example in item[etype + "_examples"]:
    #                 system_prompt = orig_prompt.replace("ToolX", tool_name)
    #                 system_prompt = system_prompt.replace("__EXAMPLE_TYPE__", "")
    #                 # user_content = f"Policy Document: {state['policy_text']}\nTools Descriptions: {json.dumps(state['tools'])}\nTarget Tool: {json.dumps(state['target_tool_description'])}\nPolicy Name: {policy['name']}\nPolicy Description: {policy['description']}\nExample: {example}"
    #                 user_content = f"""Tools Descriptions: {json.dumps(self.tools_descriptions)}
    # Target Tool: {tool.model_dump_json(indent=2)}
    # Policy Name: {item.name}
    # Policy Description: {item.description}
    # Example: {example}"""

    #                 response = await self.llm.chat_json(
    #                     generate_messages(system_prompt, user_content)
    #                 )
    #                 fixed_examples.append(response["revised_example"])
    #             item[etype + "_examples"] = fixed_examples
    #         return fixed_examples

    async def fix_spec_examples(self, tool_name: str, spec: ToolGuardSpec):
        logger.debug(f"fix_examples({tool_name})")

        orig_prompt = read_prompt_file("fix_example")
        tool = self.tools_details[tool_name]

        async def fix_item_examples(item: ToolGuardSpecItem):
            async def fix_example(example: str):
                system_prompt = orig_prompt.replace("ToolX", tool_name)
                system_prompt = system_prompt.replace("__EXAMPLE_TYPE__", "")
                user_content = f"""Tools Descriptions: {json.dumps(self.tools_descriptions)}
Target Tool: {tool.model_dump_json(indent=2)}
Policy Name: {item.name}
Policy Description: {item.description}
Example: {example}"""

                response = await self.llm.chat_json(
                    generate_messages(system_prompt, user_content)
                )
                return response["revised_example"]

            item.compliance_examples = await asyncio.gather(
                *[fix_example(ex) for ex in item.compliance_examples]
            )
            item.violation_examples = await asyncio.gather(
                *[fix_example(ex) for ex in item.violation_examples]
            )

        await asyncio.gather(*[fix_item_examples(item) for item in spec.policy_items])

        save_output(self.out_dir, f"{tool_name}_fix_examples.json", spec)

    # todo: change to revew examples, write prompts
    async def review_examples(self, tool_name: str, spec: ToolGuardSpec):
        logger.debug(f"review_examples({tool_name})")
        system_prompt = read_prompt_file("examples_reviewer")
        tool = self.tools_details[tool_name]

        async def review_item_examples(item: ToolGuardSpecItem):
            logger.debug(item.name)

            async def keep_example(example: str):
                reviews = await asyncio.gather(
                    *[review_example(example) for time in range(5)]
                )
                return self.keep_example(reviews)

            async def review_example(example: str):
                user_content = f"""Tools Descriptions: {json.dumps(self.tools_descriptions)}
Target Tool: {tool.model_dump_json(indent=2)}
Policy Name: {item.name}
Policy Description: {item.description}
Example: {example}"""
                return await self.llm.chat_json(
                    generate_messages(system_prompt, user_content)
                )

            keeps = await asyncio.gather(
                *[keep_example(ex) for ex in item.compliance_examples]
            )
            item.compliance_examples = [
                ex for ex, keep in zip(item.compliance_examples, keeps) if keep
            ]

            keeps = await asyncio.gather(
                *[keep_example(ex) for ex in item.violation_examples]
            )
            item.violation_examples = [
                ex for ex, keep in zip(item.violation_examples, keeps) if keep
            ]

        await asyncio.gather(
            *[review_item_examples(item) for item in spec.policy_items]
        )
        save_output(self.out_dir, f"{tool_name}_example_rev.json", spec)

    def keep_example(self, reviews) -> bool:
        bads = 0
        totals = 0
        for r in reviews:
            for vals in r.values():
                totals += 1
                if "value" not in vals:
                    logger.debug(reviews)
                elif not vals["value"]:
                    bads += 1
        if bads / totals > 0.8:
            return False
        return True


async def extract_toolguard_specs(
    policy_text: str,
    tools: List[ToolInfo],
    step1_output_dir: Path,
    llm: I_TG_LLM,
    tools2guard: Optional[List[str]] = None,  # None==all tools
    short=False,
) -> List[ToolGuardSpec]:
    if not os.path.isdir(step1_output_dir):
        os.makedirs(step1_output_dir)

    process_dir = step1_output_dir / "process"
    if not os.path.isdir(process_dir):
        os.makedirs(process_dir)
    generator = ToolGuardSpecGenerator(llm, policy_text, tools, process_dir)

    async def do_one_tool(tool_name: str) -> ToolGuardSpec:
        spec = (
            await generator.generate_minimal_policy(tool_name)
            if short
            else await generator.generate_policy(tool_name)
        )
        save_output(step1_output_dir, tool_name + ".json", spec)
        return spec

    specs = await asyncio.gather(
        *[
            do_one_tool(tool.name)
            for tool in tools
            if ((tools2guard is None) or (tool.name in tools2guard))
        ]
    )
    logger.debug("All tools done")
    return specs
