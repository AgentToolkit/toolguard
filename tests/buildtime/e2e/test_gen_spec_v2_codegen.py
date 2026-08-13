"""End to end: v2 specs -> adapter -> generated guards that actually run.

This is the acceptance test for the adapter. The `gen_spec_v2` unit tests prove
the spec shape and the `skip` classification; only these tests prove that what
comes out the other side still drives `gen_py` and produces guards the runtime
enforces.

Each test mirrors one variant of `test_calculator.py` — the same policy, the same
tool-input shape, and the same runtime assertion battery — so "does v2 cover what
v1 covers" is answered by the two files having the same variants.

Needs LLM credentials and is skipped without them. The credential-free half of
the same contract is in `tests/buildtime/gen_spec_v2/test_gen_py_contract.py`.
"""

import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar

import pytest
from dotenv import load_dotenv
from tests.examples.calculator.inputs import tool_functions as fn_tools
from tests.examples.calculator.inputs import tool_langchain as lg_tools
from tests.examples.calculator.inputs import tool_methods as mtd_tools

from toolguard.buildtime import (
    LitellmModel,
    SpecV2Options,
    generate_guard_specs_v2_full,
    generate_guards_code,
    specs_v2_to_v1,
)
from toolguard.buildtime.data_types import TOOLS
from toolguard.buildtime.llm import I_TG_LLM
from toolguard.buildtime.utils.open_api import OpenAPI
from toolguard.extra.api_to_functions import api_cls_to_functions
from toolguard.extra.langchain_to_oas import langchain_tools_to_openapi
from toolguard.runtime import (
    IToolInvoker,
    LangchainToolInvoker,
    ToolFunctionsInvoker,
    ToolMethodsInvoker,
)

# The v1 calculator e2e owns the runtime assertion battery; importing it keeps
# the two suites asserting exactly the same enforcement.
from .test_calculator import assert_toolgurards_run

POLICY_PATH = Path("tests/examples/calculator/inputs/policy_doc.md")
WORK_ROOT = Path("tests/tmp/e2e/gen_spec_v2")

# conftest's autouse fixture loads .env too late for a collection-time skipif,
# so load it here before the condition is evaluated.
load_dotenv()

requires_llm = pytest.mark.skipif(
    not os.getenv("LLM_API_KEY"),
    reason="needs LLM credentials (LLM_API_KEY)",
)

# Fewer votes and passes than the defaults: these tests exist to prove the
# v2 -> adapter -> codegen path, not to tune generation quality.
FAST = SpecV2Options(add_iterations=1, review_votes=3, example_number=2)


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


async def _build_v2_guards(
    variant: str,
    tools: TOOLS,
    known_tools: list,
    options: Optional[SpecV2Options] = None,
):
    """v2 specs -> adapter -> generated guard code, for one tool-input shape.

    Raw markdown, not v1's markdown->HTML conversion: v2's reference grounding
    strips markdown emphasis and segments on `- ` bullets, so HTML input yields
    references like "<p><strong>Division by Zero..." instead of the rule text.
    """
    policy_text = POLICY_PATH.read_text(encoding="utf-8")

    work_dir = WORK_ROOT / variant
    shutil.rmtree(work_dir, ignore_errors=True)

    specs = await generate_guard_specs_v2_full(
        policy_text,
        tools,
        llm(),
        work_dir / "specs_v2",
        source_doc=str(POLICY_PATH),
        options=options or FAST,
    )

    assert specs, "no v2 specs generated"
    assert all(item.references for spec in specs for item in spec.policy_items), (
        "every item must be grounded in the policy document"
    )
    assert all(
        item.id.startswith(spec.tool_name + ".")
        for spec in specs
        for item in spec.policy_items
    ), "every item id must be namespaced by its tool"

    v1_specs = specs_v2_to_v1(specs, known_tools=known_tools)
    assert any(not item.skip for spec in v1_specs for item in spec.policy_items), (
        "the calculator policy is argument-only, so something must be codegen-able"
    )

    return await generate_guards_code(
        tool_specs=v1_specs,
        tools=tools,
        work_dir=work_dir / "code",
        llm=llm(),
        app_name=f"calc_v2_{variant}",
    )


CALC_FUNCS = [
    fn_tools.divide_tool,
    fn_tools.add_tool,
    fn_tools.subtract_tool,
    fn_tools.multiply_tool,
    fn_tools.map_kdi_number,
]


@requires_llm
async def test_tool_functions():
    guards = await _build_v2_guards(
        "fns", CALC_FUNCS, [fn.__name__ for fn in CALC_FUNCS]
    )

    await assert_toolgurards_run(guards, ToolFunctionsInvoker(CALC_FUNCS))


@requires_llm
async def test_tool_methods():
    fns = api_cls_to_functions(mtd_tools.CalculatorTools)

    guards = await _build_v2_guards("mtds", fns, [fn.__name__ for fn in fns])

    await assert_toolgurards_run(
        guards, ToolMethodsInvoker(mtd_tools.CalculatorTools())
    )


@requires_llm
async def test_tools_langchain():
    tools = [
        lg_tools.divide_tool,
        lg_tools.add_tool,
        lg_tools.subtract_tool,
        lg_tools.multiply_tool,
        lg_tools.map_kdi_number,
    ]
    oas = langchain_tools_to_openapi(tools)

    guards = await _build_v2_guards("lg", oas, [tool.name for tool in tools])

    # openapi_spec=True: OpenAPI-shaped tools take their arguments wrapped.
    await assert_toolgurards_run(guards, LangchainToolInvoker(tools), True)


@requires_llm
async def test_tools_openapi_spec():
    oas = OpenAPI.load_from("tests/examples/calculator/inputs/oas.json")
    oas_dict = oas.model_dump()

    guards = await _build_v2_guards("oas", oas_dict, [fn.__name__ for fn in CALC_FUNCS])

    class DummyInvoker(IToolInvoker):
        """Compute inline instead of calling a remote web method."""

        T = TypeVar("T")

        def __init__(self) -> None:
            self._funcs_by_name = {fn.__name__: fn for fn in CALC_FUNCS}

        async def invoke(
            self, toolname: str, arguments: Dict[str, Any], return_type: Type[T]
        ) -> T:
            func = self._funcs_by_name.get(toolname)
            assert callable(func), f"Tool {toolname} was not found"
            return func(**arguments)  # type: ignore[return-value]

    await assert_toolgurards_run(guards, DummyInvoker(), True)
