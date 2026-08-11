"""The five per-tool generation stages, driven by a scripted LLM.

Every stage reads LLM output, so the tests concentrate on two things: the
transformation the stage is responsible for, and what it does with a response
that is valid JSON but not the shape it asked for.
"""

from toolguard.buildtime.gen_spec_v2.models import (
    PendingType,
    PolicyItemV2,
    Trigger,
)
from toolguard.buildtime.gen_spec_v2.stages import (
    run_create,
    run_enrich,
    run_examples,
    run_expand,
    run_review,
)

from .conftest import FakeLLM

HR_RULE = "**HR** may view and edit all employees' data."
SALARY_RULE = "When an employee's **salary** is set or updated, it must be a positive amount (greater than zero)."


def _raw(slug="hr_only", name="HR only", references=None, description="only HR may"):
    return {
        "slug": slug,
        "name": name,
        "description": description,
        "references": [HR_RULE] if references is None else references,
    }


def _item(id_="update_employee.hr_only", name="HR only", **kwargs) -> PolicyItemV2:
    return PolicyItemV2(
        id=id_,
        name=name,
        description=kwargs.pop("description", "only HR may"),
        references=kwargs.pop("references", [HR_RULE]),
        **kwargs,
    )


# --- create ----------------------------------------------------------------


async def test_create_builds_items_with_tool_prefixed_ids(ctx, tool):
    llm = FakeLLM(
        {
            "create": {
                "tool_info": {"is_read_only": False, "user_enrichment": "writes"},
                "policy_items": [_raw()],
            }
        }
    )

    tool_info, items = await run_create(llm, ctx, tool)

    assert tool_info.user_enrichment == "writes"
    assert [i.id for i in items] == ["update_employee.hr_only"]
    assert items[0].trigger == Trigger.pre_tool


async def test_create_never_trusts_an_llm_supplied_tool_prefix(ctx, tool):
    # Ids are assigned in code, so a model naming the wrong tool cannot produce
    # an id that points at a different tool's spec.
    raw = _raw()
    raw.pop("slug")
    llm = FakeLLM({"create": {"policy_items": [{**raw, "id": "wrong_tool.whatever"}]}})

    _, items = await run_create(llm, ctx, tool)

    assert items[0].id == "update_employee.whatever"


async def test_create_prefers_the_slug_over_a_supplied_id(ctx, tool):
    llm = FakeLLM(
        {"create": {"policy_items": [{**_raw(), "id": "wrong_tool.whatever"}]}}
    )

    _, items = await run_create(llm, ctx, tool)

    assert items[0].id == "update_employee.hr_only"


async def test_create_drops_an_item_with_no_references(ctx, tool):
    # An item quoting nothing is not grounded in the policy document.
    llm = FakeLLM({"create": {"policy_items": [_raw(references=[])]}})

    _, items = await run_create(llm, ctx, tool)

    assert items == []


async def test_create_drops_an_unnamed_item(ctx, tool):
    llm = FakeLLM({"create": {"policy_items": [_raw(name="")]}})

    _, items = await run_create(llm, ctx, tool)

    assert items == []


async def test_create_disambiguates_colliding_slugs(ctx, tool):
    llm = FakeLLM({"create": {"policy_items": [_raw(), _raw(name="HR only again")]}})

    _, items = await run_create(llm, ctx, tool)

    assert [i.id for i in items] == [
        "update_employee.hr_only",
        "update_employee.hr_only_2",
    ]


async def test_create_defaults_a_missing_tool_info(ctx, tool):
    llm = FakeLLM({"create": {"policy_items": []}})

    tool_info, items = await run_create(llm, ctx, tool)

    assert tool_info.is_read_only is False
    assert items == []


async def test_create_tolerates_a_response_without_policy_items(ctx, tool):
    llm = FakeLLM({"create": {"nonsense": True}})

    _, items = await run_create(llm, ctx, tool)

    assert items == []


# --- expand ----------------------------------------------------------------


async def test_expand_appends_new_items(ctx, tool):
    llm = FakeLLM(
        {
            "expand": {
                "policy_items": [_raw(slug="salary_positive", name="Salary positive")]
            }
        }
    )

    items = await run_expand(llm, ctx, tool, [_item()], iterations=1)

    assert [i.id for i in items] == [
        "update_employee.hr_only",
        "update_employee.salary_positive",
    ]


async def test_expand_stops_early_when_a_pass_adds_nothing(ctx, tool):
    llm = FakeLLM({"expand": {"policy_items": []}})

    await run_expand(llm, ctx, tool, [_item()], iterations=3)

    assert llm.count("expand") == 1


async def test_expand_runs_every_iteration_while_it_keeps_finding_items(ctx, tool):
    counter = {"n": 0}

    def respond(_content):
        counter["n"] += 1
        return {
            "policy_items": [
                _raw(slug=f"extra_{counter['n']}", name=f"E{counter['n']}")
            ]
        }

    llm = FakeLLM({"expand": respond})

    items = await run_expand(llm, ctx, tool, [_item()], iterations=3)

    assert llm.count("expand") == 3
    assert len(items) == 4


async def test_expand_does_not_duplicate_an_existing_rule(ctx, tool):
    llm = FakeLLM({"expand": {"policy_items": [_raw()]}})

    items = await run_expand(llm, ctx, tool, [_item()], iterations=1)

    assert len(items) == 1


async def test_expand_drops_an_ungrounded_item(ctx, tool):
    llm = FakeLLM({"expand": {"policy_items": [_raw(slug="new", references=[])]}})

    items = await run_expand(llm, ctx, tool, [_item()], iterations=1)

    assert len(items) == 1


# --- review ----------------------------------------------------------------


def _vote(relevant=True, valid=True, reason="because"):
    return {"is_relevant": relevant, "can_be_validated": valid, "reason": reason}


async def test_review_keeps_an_item_the_majority_approves(ctx, tool):
    llm = FakeLLM({"review": _vote()})

    kept, archived = await run_review(llm, ctx, tool, [_item()], votes=3)

    assert len(kept) == 1
    assert archived == []
    assert llm.count("review") == 3


async def test_review_archives_an_item_the_majority_rejects(ctx, tool):
    llm = FakeLLM({"review": _vote(relevant=False, reason="not this tool")})

    kept, archived = await run_review(llm, ctx, tool, [_item()], votes=3)

    assert kept == []
    assert archived[0]["id"] == "update_employee.hr_only"
    assert archived[0]["stage"] == "review"
    assert "not this tool" in archived[0]["reason"]


async def test_review_archives_an_item_that_cannot_be_validated(ctx, tool):
    llm = FakeLLM({"review": _vote(valid=False)})

    kept, _ = await run_review(llm, ctx, tool, [_item()], votes=3)

    assert kept == []


async def test_review_archive_keeps_the_references_for_traceability(ctx, tool):
    llm = FakeLLM({"review": _vote(relevant=False)})

    _, archived = await run_review(llm, ctx, tool, [_item()], votes=1)

    assert archived[0]["references"] == [HR_RULE]


async def test_review_treats_a_malformed_vote_as_a_rejection(ctx, tool):
    llm = FakeLLM({"review": {"reason": "no verdict"}})

    kept, _ = await run_review(llm, ctx, tool, [_item()], votes=1)

    assert kept == []


async def test_review_makes_no_calls_without_items(ctx, tool):
    llm = FakeLLM({"review": _vote()})

    kept, archived = await run_review(llm, ctx, tool, [], votes=3)

    assert (kept, archived) == ([], [])
    assert llm.count("review") == 0


# --- enrich ----------------------------------------------------------------


def _enrich_vote(
    trigger="pre_tool",
    system_vars=None,
    tool_history=None,
    message_history=None,
    references=None,
    pending=None,
):
    return {
        "trigger": trigger,
        "requires": {
            "system_vars": system_vars if system_vars is not None else [],
            "tool_history": tool_history,
            "message_history": message_history,
        },
        "references": [HR_RULE] if references is None else references,
        "pending_for_user": pending or [],
    }


async def test_enrich_writes_trigger_and_requires(ctx, tool):
    llm = FakeLLM(
        {"enrich": _enrich_vote(trigger="post_tool", system_vars=["department"])}
    )

    items = await run_enrich(llm, ctx, tool, [_item()], votes=3)

    assert items[0].trigger == Trigger.post_tool
    assert items[0].requires.system_vars == ["department"]


async def test_enrich_drops_an_undeclared_system_variable(ctx, tool):
    llm = FakeLLM({"enrich": _enrich_vote(system_vars=["department", "is_admin"])})

    items = await run_enrich(llm, ctx, tool, [_item()], votes=1)

    assert items[0].requires.system_vars == ["department"]


async def test_enrich_drops_a_tool_history_entry_for_an_unknown_tool(ctx, tool):
    llm = FakeLLM(
        {
            "enrich": _enrich_vote(
                tool_history=[
                    {"tool": "get_employee", "params": {}},
                    {"tool": "check_blacklist", "params": {}},
                ]
            )
        }
    )

    items = await run_enrich(llm, ctx, tool, [_item()], votes=1)

    history = items[0].requires.tool_history
    assert history is not None
    assert [e.tool for e in history] == ["get_employee"]


async def test_enrich_only_validates_references_never_adds_them(ctx, tool):
    invented = "Employees must wear a badge."
    llm = FakeLLM({"enrich": _enrich_vote(references=[HR_RULE, invented])})

    items = await run_enrich(llm, ctx, tool, [_item()], votes=1)

    assert items[0].references == [HR_RULE]


async def test_enrich_keeps_original_references_when_validation_blanks_them(ctx, tool):
    llm = FakeLLM({"enrich": _enrich_vote(references=[])})

    items = await run_enrich(llm, ctx, tool, [_item()], votes=1)

    assert items[0].references == [HR_RULE]


async def test_enrich_records_a_pending_gap(ctx, tool):
    llm = FakeLLM(
        {
            "enrich": _enrich_vote(
                pending=[
                    {
                        "type": "missing_var",
                        "detail": "no blacklist variable",
                        "question": "where does blacklist status come from?",
                    }
                ]
            )
        }
    )

    items = await run_enrich(llm, ctx, tool, [_item()], votes=1)

    assert items[0].pending_for_user[0].type == PendingType.missing_var


async def test_enrich_keeps_an_item_that_is_blocked_and_otherwise_unenforceable(
    ctx, tool
):
    # Smith archives these. v2 keeps them: surfacing the gap is the point, and
    # the adapter marks anything with pending_for_user as not codegen-able.
    llm = FakeLLM(
        {
            "enrich": _enrich_vote(
                pending=[
                    {
                        "type": "missing_tool",
                        "detail": "no email tool",
                        "question": "which tool sends the email?",
                    }
                ]
            )
        }
    )

    items = await run_enrich(llm, ctx, tool, [_item()], votes=1)

    assert len(items) == 1
    assert items[0].pending_for_user[0].type == PendingType.missing_tool


async def test_enrich_tolerates_an_empty_response(ctx, tool):
    llm = FakeLLM({"enrich": {}})

    items = await run_enrich(llm, ctx, tool, [_item()], votes=1)

    assert items[0].trigger == Trigger.pre_tool
    assert items[0].references == [HR_RULE]


# --- examples --------------------------------------------------------------


async def test_examples_are_written_onto_the_item(ctx, tool):
    llm = FakeLLM(
        {
            "examples": {
                "compliance_examples": ["An HR user edits a record."],
                "violation_examples": ["An engineer edits someone else's record."],
            }
        }
    )
    item = _item()

    await run_examples(llm, ctx, tool, [item])

    assert item.compliance_examples == ["An HR user edits a record."]
    assert item.violation_examples == ["An engineer edits someone else's record."]


async def test_examples_degrade_to_empty_on_a_misshaped_response(ctx, tool):
    llm = FakeLLM({"examples": {"compliance_examples": "not a list"}})
    item = _item()

    await run_examples(llm, ctx, tool, [item])

    assert item.compliance_examples == []
    assert item.violation_examples == []


async def test_examples_can_request_a_fixed_count(ctx, tool):
    llm = FakeLLM({"examples": {"compliance_examples": [], "violation_examples": []}})

    await run_examples(llm, ctx, tool, [_item()], example_number=2)

    assert "exactly 2" in llm.calls_for("examples")[0]["content"]


async def test_examples_makes_no_calls_without_items(ctx, tool):
    llm = FakeLLM({"examples": {}})

    await run_examples(llm, ctx, tool, [])

    assert llm.count("examples") == 0
