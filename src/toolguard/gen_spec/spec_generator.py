
import asyncio
import json
import os
from pathlib import Path
from typing import List, Optional

from ..data_types import ToolInfo, ToolGuardSpec, load_tool_policy
from ..llm.i_tg_llm import I_TG_LLM
from .utils import read_prompt_file, generate_messages, save_output, find_mismatched_references

class ToolGuardSpecGenerator:
    def __init__(self, llm:I_TG_LLM, policy_document:str, tools:List[ToolInfo], out_dir:str) -> None:
        self.llm = llm
        self.policy_document = policy_document
        self.tools_descriptions = {tool.name: tool.description for tool in tools}
        self.tools_details = {tool.name: tool for tool in tools}
        self.out_dir = out_dir
    

    async def generate_minimal_policy(self, tool_name: str) -> dict:
        tptd = await self.create_policy(tool_name)
        tptd = await self.example_creator(tool_name, tptd)
        return tptd

    async def generate_policy(self, tool_name: str) -> dict:
        tptd = await self.create_policy(tool_name)
        for i in range(3):
            tptd = await self.add_policies(tool_name, tptd, i)
        tptd = await self.split(tool_name, tptd)
        tptd = await self.merge(tool_name, tptd)
        tptd = await self.review_policy(tool_name, tptd)
        tptd = await self.add_references(tool_name, tptd)
        tptd = await self.reference_correctness(tool_name, tptd)
        tptd = await self.example_creator(tool_name, tptd)
        for i in range(5):  # FIXME
            tptd = await self.add_examples(tool_name, tptd, i)
        tptd = await self.merge_examples(tool_name, tptd)
        # tptd = self.fix_examples(tool_name, tptd)
        tptd = await self.review_examples(tool_name, tptd)
        return tptd

    async def create_policy(self, tool_name: str) -> dict:
        print("policy_creator_node")
        system_prompt = read_prompt_file("create_policy")
        system_prompt = system_prompt.replace("ToolX", tool_name)
        user_content = f"Policy Document:{self.policy_document}\nTools Descriptions:{json.dumps(self.tools_descriptions)}\nTarget Tool:{self.tools_details[tool_name].model_dump_json()}\n"
        tptd = await self.llm.chat_json(generate_messages(system_prompt, user_content))
        save_output(self.out_dir, f"{tool_name}.json", tptd)
        return tptd

    async def add_policies(
        self, tool_name: str, tptd: dict, iteration: int = 0
    ) -> dict:
        print("add_policy")
        system_prompt = read_prompt_file("add_policies")
        user_content = f"Policy Document:{self.policy_document}\nTools Descriptions:{json.dumps(self.tools_descriptions)}\nTarget Tool:{self.tools_details[tool_name].model_dump_json()}\nTPTD: {json.dumps(tptd)}"
        response = await self.llm.chat_json(
            generate_messages(system_prompt, user_content)
        )

        policies = (
            response["additionalProperties"]["policy_items"]
            if "additionalProperties" in response and "policy_items" not in response
            else response["policy_items"]
        )

        for policy in policies:
            # for policy in response["policy_items"]:
            policy["iteration"] = iteration
            tptd["policy_items"].append(policy)

        save_output(self.out_dir, f"{tool_name}_ADD_{iteration}.json", tptd)
        return tptd

    async def split(self, tool_name, tptd: dict) -> dict:
        # todo: consider addition step to split policy by policy and not overall
        print("split")
        system_prompt = read_prompt_file("split")
        user_content = f"Policy Document:{self.policy_document}\nTools Descriptions:{json.dumps(self.tools_descriptions)}\nTarget Tool:{self.tools_details[tool_name].model_dump_json()}\nTPTD: {json.dumps(tptd)}"
        tptd = await self.llm.chat_json(generate_messages(system_prompt, user_content))
        save_output(self.out_dir, f"{tool_name}_split.json", tptd)
        return tptd

    async def merge(self, tool_name, tptd: dict) -> dict:
        # todo: consider addition step to split policy by policy and not overall
        print("merge")
        system_prompt = read_prompt_file("merge")
        user_content = f"Policy Document:{self.policy_document}\nTools Descriptions:{json.dumps(self.tools_descriptions)}\nTarget Tool:{self.tools_details[tool_name].model_dump_json()}\nTPTD: {json.dumps(tptd)}"
        tptd = await self.llm.chat_json(generate_messages(system_prompt, user_content))

        save_output(self.out_dir, f"{tool_name}_merge.json", tptd)
        return tptd

    def move2archive(self, reviews) -> (bool, str):
        comments = ""
        num = len(reviews)
        if num == 0:
            return False
        counts = {
            "is_relevant": 0,
            "is_tool_specific": 0,
            "can_be_validated": 0,
            "is_actionable": 0,
        }

        for r in reviews:
            print(
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

    async def review_policy(self, tool_name, tptd) -> dict:
        print("review_policy")
        system_prompt = read_prompt_file("policy_reviewer")
        newTPTD = {"policy_items": []}

        if "policy_items" not in tptd:
            tptd["policy_items"] = []

        for item in tptd["policy_items"]:
            reviews = []
            for _iteration in range(5):
                user_content = f"Policy Document:{self.policy_document}\nTools Descriptions:{json.dumps(self.tools_descriptions)}\nTarget Tool:{json.dumps(self.tools_descriptions[tool_name])}\npolicy: {json.dumps(item)}"
                response = await self.llm.chat_json(
                    generate_messages(system_prompt, user_content)
                )
                if "is_self_contained" in response:
                    is_self_contained = response["is_self_contained"]
                    if not is_self_contained:
                        if "alternative_description" in response:
                            item["description"] = response["alternative_description"]
                        else:
                            print(
                                "Error: review is_self_contained is false but no alternative_description."
                            )
                else:
                    print("Error: review did not provide is_self_contained.")
                reviews.append(response)
            archive, comments = self.move2archive(reviews)
            print(archive)
            if archive:
                if "archive" not in newTPTD:
                    newTPTD["archive"] = []
                item["comments"] = comments
                newTPTD["archive"].append(item)
            else:
                newTPTD["policy_items"].append(item)
        save_output(self.out_dir, f"{tool_name}_rev.json", newTPTD)
        return newTPTD

    async def add_references(self, tool_name: str, tptd: dict) -> dict:
        print("add_ref")
        system_prompt = read_prompt_file("add_references")
        # remove old refs (used to help avoid duplications)
        for item in tptd["policy_items"]:
            item["references"] = []
            user_content = f"Policy Document:{self.policy_document}\nTools Descriptions:{json.dumps(self.tools_descriptions)}\nTarget Tool:{self.tools_details[tool_name].model_dump_json()}\npolicy: {json.dumps(item)}"
            response = await self.llm.chat_json(
                generate_messages(system_prompt, user_content)
            )
            if "references" in response:
                item["references"] = response["references"]
            else:
                print("Error! no references in response")
                print(response)

        save_output(self.out_dir, f"{tool_name}_ref.json", tptd)
        return tptd

    async def reference_correctness(self, tool_name: str, tptd: dict) -> dict:
        print("reference_correctness")
        tptd, unmatched_policies = find_mismatched_references(
            self.policy_document, tptd
        )
        save_output(self.out_dir, f"{tool_name}_ref_orig_.json", unmatched_policies)
        save_output(self.out_dir, f"{tool_name}_ref_correction_.json", tptd)
        return tptd

    async def example_creator(self, tool_name: str, tptd: dict) -> dict:
        print("example_creator")
        system_prompt = read_prompt_file("create_examples")
        system_prompt = system_prompt.replace("ToolX", tool_name)

        for item in tptd["policy_items"]:
            # user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nPolicy:{policy}"
            user_content = f"Tools Descriptions:{json.dumps(self.tools_descriptions)}\nTarget Tool:{self.tools_details[tool_name].model_dump_json()}\nPolicy:{item}"

            response = await self.llm.chat_json(
                generate_messages(system_prompt, user_content)
            )
            if "violation_examples" in response:
                item["violation_examples"] = response["violation_examples"]

            if "compliance_examples" in response:
                item["compliance_examples"] = response["compliance_examples"]

        save_output(self.out_dir, f"{tool_name}_examples.json", tptd)
        return tptd

    async def add_examples(self, tool_name: str, tptd: dict, iteration: int) -> dict:
        print("add_examples")
        system_prompt = read_prompt_file("add_examples")
        system_prompt = system_prompt.replace("ToolX", tool_name)
        for item in tptd["policy_items"]:
            # user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nPolicy:{policy}"
            user_content = f"Tools Descriptions:{json.dumps(self.tools_descriptions)}\nTarget Tool:{self.tools_details[tool_name].model_dump_json()}\nPolicy:{item}"
            response = await self.llm.chat_json(
                generate_messages(system_prompt, user_content)
            )
            if "violation_examples" in response:
                for vexample in response["violation_examples"]:
                    # vexample["iteration"] = state["iteration"]
                    if "violation_examples" not in item:
                        item["violation_examples"] = []
                    item["violation_examples"].append(vexample)
            if "compliance_examples" in response:
                for cexample in response["compliance_examples"]:
                    if "compliance_examples" not in item:
                        item["compliance_examples"] = []
                    # cexample["iteration"] = state["iteration"]
                    item["compliance_examples"].append(cexample)

        save_output(self.out_dir, f"{tool_name}_ADD_examples{iteration}.json", tptd)
        return tptd

    async def merge_examples(self, tool_name: str, tptd: dict) -> dict:
        print("merge_examples")
        system_prompt = read_prompt_file("merge_examples")
        system_prompt = system_prompt.replace("ToolX", tool_name)
        for item in tptd["policy_items"]:
            # user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nPolicy Name:{policy['name']}\nPolicy Description:{policy['description']}"
            user_content = f"Tools Descriptions:{json.dumps(self.tools_descriptions)}\nTarget Tool:{self.tools_details[tool_name].model_dump_json()}\nPolicy Name:{item['name']}\nPolicy Description:{item['description']}"
            user_content += f"\n\nviolation Examples: {item['violation_examples']}"
            user_content += f"\n\nCompliance Examples: {item['compliance_examples']}"
            response = await self.llm.chat_json(
                generate_messages(system_prompt, user_content)
            )
            item["violation_examples"] = response["violation_examples"]
            item["compliance_examples"] = response["compliance_examples"]

        save_output(self.out_dir, f"{tool_name}_merge_examples.json", tptd)
        return tptd

    async def fix_examples(self, tool_name: str, tptd: dict) -> dict:
        print("fix_examples")
        orig_prompt = read_prompt_file("fix_example")
        for item in tptd["policy_items"]:
            for etype in ["violation", "compliance"]:
                fixed_examples = []
                for example in item[etype + "_examples"]:
                    system_prompt = orig_prompt.replace("ToolX", tool_name)
                    system_prompt = system_prompt.replace("__EXAMPLE_TYPE__", "")

                    # user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nPolicy Name:{policy['name']}\nPolicy Description:{policy['description']}\nExample:{example}"
                    user_content = f"Tools Descriptions:{json.dumps(self.tools_descriptions)}\nTarget Tool:{self.tools_details[tool_name].model_dump_json()}\nPolicy Name:{item['name']}\nPolicy Description:{item['description']}\nExample:{example}"

                    response = await self.llm.chat_json(
                        generate_messages(system_prompt, user_content)
                    )
                    fixed_examples.append(response["revised_example"])
                item[etype + "_examples"] = fixed_examples

        save_output(self.out_dir, f"{tool_name}_fix_examples.json", tptd)
        return tptd

    # todo: change to revew examples, write prompts
    async def review_examples(self, tool_name: str, tptd: dict) -> dict:
        print("review_examples")
        system_prompt = read_prompt_file("examples_reviewer")
        for item in tptd["policy_items"]:
            print(item["name"])
            for etype in ["violation", "compliance"]:
                print(etype)
                passed_examples = []
                for example in item[etype + "_examples"]:
                    print(example)
                    reviews = []
                    for _iteration in range(5):
                        # user_content = f"Policy Document:{state['policy_text']}\nTools Descriptions:{json.dumps(state['tools'])}\nTarget Tool:{json.dumps(state['target_tool_description'])}\nPolicy Name:{policy['name']}\nPolicy Description:{policy['description']}\nExample:{example}"
                        user_content = f"Tools Descriptions:{json.dumps(self.tools_descriptions)}\nTarget Tool:{self.tools_details[tool_name].model_dump_json()}\nPolicy Name:{item['name']}\nPolicy Description:{item['description']}\nExample:{example}"
                        response = await self.llm.chat_json(
                            generate_messages(system_prompt, user_content)
                        )
                        reviews.append(response)
                    keep = self.keep_example(reviews)
                    if keep:
                        passed_examples.append(example)

                item[etype + "_examples"] = passed_examples

        save_output(self.out_dir, f"{tool_name}_example_rev.json", tptd)
        return tptd

    def keep_example(self, reviews) -> bool:
        bads = 0
        totals = 0
        for r in reviews:
            for vals in r.values():
                totals += 1
                if "value" not in vals:
                    print(reviews)
                elif not vals["value"]:
                    bads += 1
        if bads / totals > 0.8:
            return False
        return True


async def extract_toolguard_specs(
    policy_text: str,
    tools: List[ToolInfo],
    step1_output_dir: str,
    llm: I_TG_LLM,
    tools_shortlist: Optional[List[str]] = None,
    short=False,
) -> List[ToolGuardSpec]:
    if not os.path.isdir(step1_output_dir):
        os.makedirs(step1_output_dir)

    process_dir = os.path.join(step1_output_dir, "process")
    if not os.path.isdir(process_dir):
        os.makedirs(process_dir)
    tpg = ToolGuardSpecGenerator(llm, policy_text, tools, process_dir)

    async def do_one_tool(tool_name)->ToolGuardSpec:
        spec_dict = await tpg.generate_minimal_policy(tool_name) if short \
            else await tpg.generate_policy(tool_name)
        spec = ToolGuardSpec(tool_name=tool_name, **spec_dict)

        path = Path(step1_output_dir, tool_name + ".json")
        path.write_text(
            spec.model_dump_json(indent=2),
            encoding="utf-8"
        )
        return spec

    specs = await asyncio.gather(
        *[
            do_one_tool(tool.name)
            for tool in tools
            if ((tools_shortlist is None) or (tool.name in tools_shortlist))
        ]
    )
    print("All tools done")
    return specs