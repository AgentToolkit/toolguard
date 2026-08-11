"""What guards v1 produces versus v2-via-adapter, over identical inputs.

Neither generator is "correct" by definition, so this reports rather than
asserts: it runs both step-1 pipelines on the same policy and tools, computes
the set of items each would hand to codegen, and writes the difference to a
markdown file. The point is to make the migration cost visible — v2 has a
different prompt lineage and a different stage list, so its guard set is not
expected to match v1's.

Reading the report:
- **v1 only** — a guard you would lose by switching. Worth understanding.
- **v2 only** — a rule v1 missed or deleted.
- **skipped by v2** — rules v2 captured but that today's codegen cannot enforce
  (identity, conversation, post-call, or an open question). These are the honest
  gap, not a regression: v1 dropped them silently.

Needs LLM credentials and runs two full spec generations, so it is opt-in via
`-m delta`.
"""

import os
from pathlib import Path
from typing import Dict, List

import pytest
from dotenv import load_dotenv
from examples.calculator.inputs import tool_functions as fn_tools

from toolguard.buildtime import (
    LitellmModel,
    SpecV2Options,
    generate_guard_specs,
    generate_guard_specs_v2_full,
    specs_v2_to_v1,
)
from toolguard.buildtime.gen_spec_v2.models import slugify
from toolguard.buildtime.llm import I_TG_LLM

load_dotenv()

POLICY_PATH = Path("tests/examples/calculator/inputs/policy_doc.md")
WORK_ROOT = Path("tests/tmp/e2e/guard_set_delta")
REPORT_PATH = WORK_ROOT / "guard_set_delta.md"

requires_llm = pytest.mark.skipif(
    not os.getenv("LLM_API_KEY"),
    reason="needs LLM credentials (LLM_API_KEY)",
)

CALC_FUNCS = [
    fn_tools.divide_tool,
    fn_tools.add_tool,
    fn_tools.subtract_tool,
    fn_tools.multiply_tool,
    fn_tools.map_kdi_number,
]


def llm() -> I_TG_LLM:
    return LitellmModel(
        model_name=os.getenv("MODEL_NAME") or "gpt-4o-2024-08-06",
        provider=os.getenv("LLM_PROVIDER") or "azure",
        kw_args={
            "api_base": os.getenv("LLM_API_BASE"),
            "api_version": os.getenv("LLM_API_VERSION"),
            "api_key": os.getenv("LLM_API_KEY"),
        },
    )


def _guard_set(specs) -> Dict[str, List[str]]:
    """Tool -> names of items codegen would receive (i.e. not skipped)."""
    return {
        spec.tool_name: sorted(i.name for i in spec.policy_items if not i.skip)
        for spec in specs
    }


def _skipped(specs) -> Dict[str, List[str]]:
    return {
        spec.tool_name: sorted(
            f"{i.name} — {i.debug.get('skip_reason', 'skipped')}"
            for i in spec.policy_items
            if i.skip
        )
        for spec in specs
    }


def _render(v1: Dict[str, List[str]], v2: Dict[str, List[str]], skipped) -> str:
    """Render the comparison, matching rules by slug rather than exact name.

    The two generators word an item's `name` differently for the same rule —
    v1 tends to copy the policy heading, v2 writes a sentence — so comparing
    raw names puts every rule in both "only" columns and reads as though every
    guard were lost and replaced. Slugs collapse that cosmetic difference so the
    columns show rules that genuinely exist on one side only.
    """
    lines = [
        "# Guard-set delta: v1 vs v2-via-adapter",
        "",
        f"Policy: `{POLICY_PATH}`  ",
        f"Model: `{os.getenv('MODEL_NAME')}`",
        "",
        "Rules are matched by slug, so a rule both generators found is not listed as",
        '"only" just because they worded its name differently.',
        "",
        "| Tool | v1 guards | v2 guards | v1 only | v2 only |",
        "|---|---|---|---|---|",
    ]
    for tool in sorted(set(v1) | set(v2)):
        a = {slugify(name): name for name in v1.get(tool, [])}
        b = {slugify(name): name for name in v2.get(tool, [])}
        only_a = [a[s] for s in sorted(set(a) - set(b))]
        only_b = [b[s] for s in sorted(set(b) - set(a))]
        lines.append(
            f"| `{tool}` | {len(a)} | {len(b)} | "
            f"{'; '.join(only_a) or '—'} | {'; '.join(only_b) or '—'} |"
        )

    lines += ["", "## Captured by v2 but not enforceable today", ""]
    any_skipped = False
    for tool in sorted(skipped):
        for entry in skipped[tool]:
            any_skipped = True
            lines.append(f"- `{tool}`: {entry}")
    if not any_skipped:
        lines.append("_none_")

    lines += [
        "",
        "## Totals",
        "",
        f"- v1 guards: {sum(len(v) for v in v1.values())}",
        f"- v2 guards: {sum(len(v) for v in v2.values())}",
        f"- v2 captured but not enforceable: {sum(len(v) for v in skipped.values())}",
        "",
    ]
    return "\n".join(lines)


@pytest.mark.delta
@requires_llm
async def test_report_guard_set_delta():
    policy_markdown = POLICY_PATH.read_text(encoding="utf-8")
    WORK_ROOT.mkdir(parents=True, exist_ok=True)

    v1_specs = await generate_guard_specs(
        policy_text=policy_markdown,
        tools=CALC_FUNCS,
        llm=llm(),
        work_dir=WORK_ROOT / "v1",
    )

    v2_specs = await generate_guard_specs_v2_full(
        policy_markdown,
        CALC_FUNCS,
        llm(),
        WORK_ROOT / "v2",
        source_doc=str(POLICY_PATH),
        options=SpecV2Options(),
    )
    v2_as_v1 = specs_v2_to_v1(v2_specs, known_tools=[fn.__name__ for fn in CALC_FUNCS])

    v1_set, v2_set = _guard_set(v1_specs), _guard_set(v2_as_v1)
    report = _render(v1_set, v2_set, _skipped(v2_as_v1))
    REPORT_PATH.write_text(report, encoding="utf-8")
    print("\n" + report)

    # Reporting, not asserting equality: the only hard requirement is that
    # neither generator came back empty, which would mean the run failed rather
    # than that the generators disagree.
    assert sum(len(v) for v in v1_set.values()) > 0, "v1 produced no guards"
    assert sum(len(v) for v in v2_set.values()) > 0, "v2 produced no guards"
    assert REPORT_PATH.exists()
