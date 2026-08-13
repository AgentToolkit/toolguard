# gen_spec_v2 — Design

Date: 2026-08-10
Status: implemented — see "Implementation notes" for decisions made while building
Related: `src/toolguard/buildtime/gen_spec/` (v1), `~/workspace/smith/src/smith/spec_generation/`,
ground-truth fixtures at `~/workspace/smith/examples/employee/smith/smith_outputs/ground_truth_specs/`,
superseded design on branch `v2-abandoned-extend-gen_spec`

## Problem

Toolguard's step-1 spec generator emits a flat spec: per item a `name`, `description`,
`references`, examples, and a `skip` flag. That shape cannot express things the policy
documents we care about actually say:

- **who** is acting (the acting user's id, department, organization)
- **when** a rule applies — before the call, or against the call's result
- **what else** is needed to decide — a prior tool call, or the chat history
- **what is missing** — a tool that does not exist, a variable nobody supplies, or a
  question only a human can answer

Rules of those kinds are currently deleted by the feasibility step, so the output looks
complete while silently dropping most of a real policy.

`gen_spec_v2` is a second, parallel generator that emits a richer per-tool spec covering
all of the above. It lives beside v1, not in place of it; v1 is untouched and stays the
default until v2 proves itself.

## Decisions

| Decision | Choice |
|---|---|
| Implementation lineage | Port smith's `spec_generation` package, adapted to toolguard's `I_TG_LLM` / `ToolInfo` / prompt-file conventions |
| Downstream reach | Spec generation plus a pure `SpecV2 → ToolGuardSpec` adapter so `gen_py` can consume v2 output today |
| Cross-tool work | Two entry points (per-tool, conflicts) plus an all-in-one; **no `global.json`** |
| Orphan-rule coverage report | Out of scope |
| Adapter `skip` rule | `pending_for_user` or `message_history` or `post_tool` or `system_vars` |
| On-disk format | Byte-compatible with smith's serializer (key order, omit-when-empty) |
| Policy-document parsing | Fuzzy reference grounding, no bullet requirement — with the matcher rewritten |
| Blocking-gap items | Kept in `policy_items` carrying their alert, not archived |

## Architecture

```
buildtime/gen_spec_v2/
  models.py       pydantic schema + Trigger / PendingType enums, slugify, unique_id
  serialize.py    ordered writer / tolerant reader (byte parity)
  sysvars.py      load sys_var.json (dict or path), normalize, render
  context.py      GenContext + pure render_* helpers
  tools_input.py  TOOLS | list[ToolInfo] -> list[ToolInfo]  (v1 is not touched)
  refmatch.py     reference grounding — rewritten, not ported
  reconcile.py    pure enrich-vote reconciliation
  adapter.py      SpecV2 -> runtime ToolGuardSpec
  conflicts.py    pairwise detection + routing
  pipeline.py     per-tool orchestration + entry points
  stages/         create, expand, review, enrich, examples
  prompts/        *.txt system prompts
```

Smith's prompts are Python modules that build both the system text and the user content.
v2 splits that: system text in `prompts/*.txt` (toolguard's `read_prompt_file`
convention), user-content assembly in `context.render_*`.

`models`, `serialize`, `sysvars`, `refmatch`, `reconcile`, `adapter`, and conflict
routing are pure — no LLM, no I/O. The tests concentrate there.

`gen_spec_v2/prompts` must be added to `[tool.hatch.build.targets.wheel.sources]` in
`pyproject.toml`, or the prompts do not ship in the wheel.

## 1. Schema

Pydantic models in `gen_spec_v2/models.py`. Buildtime-only: the runtime never sees them,
the adapter is the bridge.

```
Requires{system_vars: list[str], tool_history: list[ToolHistoryEntry] | None,
         message_history: bool | None}
ToolHistoryEntry{tool: str, params: dict[str, str]}
PendingItem{type: PendingType, detail, question, suggested_tool?, suggested_source?}
Resolution{answer, decided_by, effect}
ResolvedItem = PendingItem + resolution
PolicyItemV2{id, name, description, compliance_examples, violation_examples,
             references, trigger: Trigger, requires, pending_for_user, resolved_by_user}
Conflict{id, name, kind, conflicting_policies, description, question, resolution?}
SpecToolInfo{is_read_only: bool, user_enrichment: str}
SpecDebugV2{tool_info, archive: list[dict], notes: list | None}
SpecV2{tool_name, source_doc, policy_items, conflicts, debug}
```

`SpecToolInfo` avoids colliding with the existing `ToolInfo` (tool signatures, a
different concept); it still serializes under the key `tool_info`.

Two enums where smith uses bare strings:

- `Trigger = pre_tool | post_tool`
- `PendingType = missing_tool | missing_var | clarification`

`PendingType` normalizes aliases on read (`missing_variable` → `missing_var`). This fixes
a live bug: smith's enrich prompt asks for `missing_var`, but two ground-truth specs
contain `missing_variable`, and smith's archive check only matches `missing_var` — so
those gaps were never recognized as blocking. Under v2's "keep the item" rule the
normalization is safe; it would have been load-bearing under smith's "archive" rule.

### Serialization

Pydantic emits declaration order, so `serialize.py` writes explicitly:

```
item:  id, name, description, compliance_examples, violation_examples,
       references, trigger, requires, [pending_for_user], [resolved_by_user]
spec:  tool_name, source_doc, policy_items, [conflicts], debug
```

`[...]` is omitted when empty, as are `suggested_tool` / `suggested_source` when null and
`debug.notes` when absent. Output is `json.dumps(..., indent=2, ensure_ascii=False)` plus
a trailing newline — smith's exact bytes.

## 2. Inputs

```python
generate_guard_specs_v2(
    policy_text: str,
    tools: TOOLS | list[ToolInfo],
    llm: I_TG_LLM,
    work_dir: str | Path,
    *,
    tools2guard: list[str] | None = None,
    system_vars: dict | str | Path | None = None,
    source_doc: str = "",
    options: SpecV2Options | None = None,
) -> list[SpecV2]
```

- **policy_text** — free-form. No bullet structure required.
- **tools** — callables, an OpenAPI dict, or a `list[ToolInfo]`. MCP servers arrive
  through the existing `extra/mcp_tools_to_oas.py` path. `tools_input.py` implements the
  `list[ToolInfo]` branch inside v2 so `gen_spec`'s `_tools_to_tool_infos` is not touched.
- **system_vars** — a dict, or a path to `sys_var.json`. Every top-level key is a subject
  variable except `action_list` and `action_description`, which describe the agent's
  tools rather than the acting user.

`sys_var.json` value semantics, rendered into every stage's prompt:

| Value shape | Rendered as |
|---|---|
| list — `"department": ["HR", ...]` | allowed values |
| scalar — `"user_id": 1` | example value |
| nested mapping or list — `"entitlements": {...}` | example value, rendered as-is |

Each renders with its `input.extensions.subject.<name>` path so the LLM names only
variables that exist. `requires.system_vars` is validated against those names; an
invented name is dropped and logged.

`SpecV2Options`: `review_votes=5`, `enrich_votes=3`, `add_iterations=3`,
`include_examples=True`, `example_number=None`, `max_concurrency=8`,
`on_tool_error="skip" | "raise"`.

## 3. Pipeline

Per tool, in order: **create → expand ×N → review → enrich → examples**.

| Stage | Does |
|---|---|
| `create` | Extracts the tool's policy items, plus `debug.tool_info{is_read_only, user_enrichment}`. Ids are assigned in code — `unique_id(tool, slugify(name), taken)` → `add_department.hr_only` — never by the LLM. |
| `expand` | `add_iterations` passes adding items the earlier passes missed. New items get ids the same way. |
| `review` | `review_votes` relevance votes per item; losers move to `debug.archive` as `{id, name, reason, stage}`. |
| `enrich` | `enrich_votes` votes per item, reconciled by a pure function. Produces `trigger`, `requires`, `pending_for_user`, and reference *validation*. |
| `examples` | Compliance / violation examples per item. |

`enrich` is where the four alerts come from, in one vote payload:

| Ask | Field |
|---|---|
| pre-tool vs post-tool | `trigger` |
| a tool call is needed first | `requires.tool_history` — with the params to call it with |
| the chat history is needed | `requires.message_history` |
| a missing tool / missing system var | `pending_for_user[type=missing_tool \| missing_var]` |
| a clarification question is needed | `pending_for_user[type=clarification]` |

Reconciliation (`reconcile.py`, pure): majority `trigger` with ties → `pre_tool`; sorted
union of `system_vars`; the longest `tool_history` unless a strict majority say null;
`message_history` true on a strict majority; `pending_for_user` deduped by
`(type, question)`, first occurrence winning.

Enrich only **validates** references — its result is intersected with the references the
item arrived with, so a vote can keep or drop but never add. If validation would blank a
grounded set, the original set is kept.

Unlike smith, an item with a `missing_tool` / `missing_var` gap and no other enforcement
source is **kept**, carrying its alert. That is the point of the feature. Nothing
downstream is endangered: the adapter marks anything with `pending_for_user` as skipped.

Per-tool failures are isolated under `asyncio.Semaphore(max_concurrency)`;
`on_tool_error="skip"` records the failure and lets the other tools finish.

## 4. Entry points

| Function | Does |
|---|---|
| `generate_guard_specs_v2` | Per-tool specs → `<tool>.json`. No cross-tool work. |
| `generate_spec_conflicts_v2` | Pairwise within-tool conflict detection over a spec set — passed in, or every `<tool>.json` loaded from `work_dir`. Rewrites specs whose `conflicts` changed. |
| `generate_guard_specs_v2_full` | All tools, then conflicts. One call for a full build. |

Conflict detection is within-tool pairwise upper-triangle (item `i` vs items `i+1..n`),
which keeps every prompt bounded by one tool's item count. A conflict can still name ids
from other tools, so routing handles both cases:

- all `conflicting_policies` share one tool prefix → attach to that tool's spec
- prefixes span several tools → attach to **each** involved tool's spec, deduped by id,
  so every spec stays self-contained (smith sent these to `global.json`, which v2 does
  not have)

## 5. Reference grounding

v1's `find_mismatched_references` has five concrete defects:

1. `normalize_text` only lowercases, so a reference differing by line wrap, `**bold**`,
   or an em-dash versus a hyphen never matches.
2. `end_idx = start_idx + len(reference)` projects a normalized match back using the
   *reference's* length — correct only while normalization is length-preserving. Any real
   normalization silently yields truncated or over-long quotes.
3. The fallback splits a reference in two and accepts it if each half appears *anywhere*;
   a half can be one word matched in an unrelated section.
4. No fuzzy matching — the `difflib` attempt is commented out.
5. `unmatched_policies` is computed, returned, and discarded by the caller. No signal.

`refmatch.py` replaces it. Still fuzzy — no bullet requirement:

- `normalize(text) -> (str, offsets)` — NFKC, casefold, unify dashes and quotes, strip
  markdown emphasis and backticks, collapse whitespace, **with a normalized→original
  offset map** so every match projects back to an exact original substring regardless of
  length change.
- `segments(doc) -> list[Span]` — candidate units with original spans: bullet lines where
  present, otherwise sentences within paragraphs. Boundaries are preferred, never
  required.
- `ground(reference, doc)` — in order: exact normalized substring, snapped outward to the
  enclosing segment when the match covers most of it; else the best segment by
  `difflib.SequenceMatcher` ratio above a named threshold (stdlib, no new dependency);
  else 2+ **consecutive** segments covering the reference, replacing the arbitrary
  two-part split; else `None`.
- `ground_spec(spec, policy_text)` — rewrites references to grounded verbatim spans,
  dedupes, preserves order. An ungrounded reference is kept as written **and** recorded in
  `debug` with a warning, so nothing silently passes a paraphrase off as a quote.

Prompt side: create and expand ask for verbatim contiguous quotes, one per rule, no
ellipsis, no paraphrase.

## 6. Adapter and `gen_py` compatibility

`adapter.spec_v2_to_v1(spec) -> ToolGuardSpec`, pure:

```python
skip = (bool(item.pending_for_user)
        or bool(item.requires.message_history)
        or item.trigger == Trigger.post_tool
        or bool(item.requires.system_vars))
```

Each condition marks something today's codegen and runtime cannot enforce *correctly* —
generated guards receive `args` + `api` only, with no subject and no message history, and
there is no post-invocation hook. A guard generated anyway would be wrong enforcement
rather than absent enforcement. Each condition drops out as the runtime gains that
capability.

`id`, `trigger`, and `requires` ride along in `item.debug`; `source_doc`, `conflicts`,
`tool_info`, and `archive` in `spec.debug`.

`gen_py` consumes exactly five fields, which pins the adapter's contract:

| Field | Used for | Adapter consequence |
|---|---|---|
| `spec.tool_name` | guard module + function name | Must not emit specs for tools absent from `tools` |
| `item.name` | python module, function, and test-file names (`.` → `_` in place) | v2 names are human sentences like v1's. Two items in one tool sharing a name would collide on one file — `unique_id` dedupes ids, not names — so the adapter disambiguates a colliding name with the id suffix |
| `item.description` | the pseudo-code prompt that becomes the guard body | unchanged |
| `item.compliance_examples` / `violation_examples` | test generation | unchanged |
| `item.skip` | `[i for i in spec.policy_items if not i.skip]`, then specs with zero items are dropped | the filter above |

Two consequences to expect:

- **Most employee-example tools produce no guards.** When every rule for a tool is
  system-var-driven, all its items are skipped and `gen_toolguards` drops the spec. That
  is correct. The "adapter drives gen_py" test therefore runs on calculator/tau2, where
  items survive; the employee example is used to assert the *skip classification*.
- `update_employee.home_address_same_country` needs `tool_history: [get_employee]` but no
  system vars, no chat history, and is `pre_tool` — so it is **not** skipped and does get
  codegen'd. `tool_dependencies.py` then re-infers `get_employee` with an LLM call even
  though `requires.tool_history` states it. Harmless now; the most obvious first win when
  `gen_py` learns v2 natively.

### Known compatibility caveat

v2 writes `<tool>.json` — the same filenames v1 uses. Pydantic's default
`extra='ignore'` means v1's `ToolGuardSpec.load` *accepts* a v2 file silently, dropping
`id` / `trigger` / `requires` / `pending_for_user` and yielding every item `skip=False`.
Since `gen_toolguards` filters on `skip`, a caller that globs a shared spec directory
would generate wrong-enforcement guards. Documented, not fixed: point v2 at its own
`work_dir`, which is what the docs and tests do.

## 7. Testing

| Layer | Test | LLM |
|---|---|---|
| Serializer | Each ground-truth fixture: load → dump → identical bytes (modulo `missing_variable` → `missing_var`) | no |
| Models | Enum aliasing; optional keys absent/present; tolerant read | no |
| `sysvars` | dict and path inputs; list → allowed values, scalar → example value | no |
| `refmatch` | Exact; line-wrapped; markdown-stripped; em-dash vs hyphen; mid-sentence snap; two consecutive segments; no match; offset projection under length-changing normalization | no |
| `reconcile` | Tie → `pre_tool`; union of `system_vars`; majority-null `tool_history`; `message_history` majority; pending dedupe | no |
| `adapter` | `skip` truth table; name-collision disambiguation; output loads through `ToolGuardSpec.load` | no |
| Conflicts | Single-prefix → that tool; multi-prefix → each involved tool | no |
| Pipeline | Fake LLM: per-tool isolation, `on_tool_error`, partial regeneration leaves other files untouched, conflicts entry point loads from disk | no |
| e2e | v2 → adapter → `generate_guards_code`: guards compile and their generated tests pass (calculator) | yes |
| e2e | Employee policy + MCP server → shape parity with ground truth: every tool file present, ids well-formed, trigger/requires on every item, pending types in the enum | yes |

Ground-truth fixtures live in `tests/examples/employee_mini/` — a committed six-spec
slice of smith's employee output, chosen so the byte-parity, grounding and
identifier gates run in a plain clone without a cross-repo dependency. The full
28-spec example and its benchmarks belong to the evaluate-toolguard project; see
that directory's README for the three derivations applied.

## Implementation notes

Decisions taken while building, beyond what the design above specified.

**Two non-subject keys are excluded by name; every value shape is kept.** The design
said toolguard applies no filtering and the caller passes a clean dict. The real
`system_vars.json` carries `action_list` (34 tool names) and `action_description` (a
35-entry mapping) alongside the four subject variables, and rendering those into every
prompt is noise — they describe the agent's own tools, not the acting user.
`load_system_vars` drops exactly those two keys (`NON_SUBJECT_KEYS`).

`sys_var.json` is **not** assumed to be flat: a nested mapping or list is kept and
rendered as a subject variable, since a structured attribute of the acting user is
still an attribute of the acting user. A list renders as allowed values; anything else
renders as an example value.

**Ungrounded references are recorded in `debug.notes`.** `notes` is
presence-tracked and omitted when absent, so a spec whose every reference grounded is
byte-identical to smith's output; only a spec with a quote that could not be located
carries the extra key.

**Enrich validates against reality, not just across votes.** Beyond reconciliation, an
undeclared system variable and a `tool_history` entry naming a tool that does not exist
are both dropped with a warning. Either would otherwise compile into a guard reading
something that is not there.

**Conflicts naming no known policy item are dropped**, and `attach_conflicts` replaces
rather than appends, so rerunning the conflicts pass is idempotent.

**Adapter name disambiguation happens in codegen's namespace.** Comparing raw names was
not enough: `gen_py` rewrites `.` to `_` and then snake-cases, so "rule v1.0" and
"rule v1_0" are different names that land in the same generated file. The adapter now
keys collisions on `to_py_module_name(f"guard_{name.replace('.', '_')}")`. The
disambiguating suffix is appended with a space and no punctuation, because
`to_snake_case` leaves punctuation in place.

**A pre-existing v1 limitation, found and not fixed:** `to_snake_case` does not strip
parentheses, so an item named "Flight booking passenger limit (foreign-domain rule)"
yields `guard_flight_booking_passenger_limit_(foreign_domain_rule)` — not a valid
python identifier. It bites only unskipped items, and every parenthesized name in the
employee corpus is skipped, so nothing breaks today. Fixing `py.to_snake_case` was out
of scope ("no change to v1"); the adapter's own suffix is punctuation-free so it cannot
walk into the same hole.

**`on_tool_error` defaults to `skip`**, so one tool's failure never costs a whole run.
Every requested tool gets a spec file even when no rule governs it: an empty spec is a
real answer, and its absence would be indistinguishable from a failed run.

### Over-attachment: found by the tau2 port, fixed in the prompts

The first tau2 run exposed a real defect. On the one-sentence policy "Users cannot book a
flight for more than 5 passengers", v1 binds the rule to two tools; v2 bound it to five,
adding `update_reservation_baggages`, `update_reservation_flights`, and
`transfer_to_human_agents`. On the cancellation policy, v2 additionally bound rules to
`book_reservation`, `get_reservation_details`, and `get_flight_status`.

These were not hallucinations — each cited the correct policy line — but they were bound
to tools the policy does not govern, and they were **not** skipped by the adapter, so
guards were generated: four guarded tools instead of two, including one on
`get_reservation_details`, a read-only lookup. A false guard on an unrelated tool is worse
than a missing guard: it denies legitimate calls.

The cause was in the prompts. `review.txt` said "do NOT reject an item merely because the
same rule also applies to other tools", which is right for genuine cross-cutting rules
(confirm-before-write applies to every write tool) but was read as licence to bind any
rule to any tool touching the same record.

The fix is one criterion, added to `create.txt`, `expand.txt`, and `review.txt`:

> Is there some set of arguments for which calling THIS tool performs the action the rule
> restricts, or produces the state the rule forbids?

It separates the two cases cleanly. `update_reservation_passengers` can set six
passengers, so the cap governs it; `update_reservation_baggages` cannot change the
passenger count under any arguments, so it does not. A write tool does perform the write
that confirm-before-write restricts, so cross-cutting rules still bind. `create.txt`
additionally requires each `description` to name both the action of *this* tool being
restricted and the exact value tested, and to omit the item when it cannot.

Sharpening the prompts took tau2 `simple` from five governed tools to three and
`complex_api` from five to one (correct), but did not fully close it.
`update_reservation_flights` still binds the passenger cap, and its own description says
why it should not: *"The passenger count is not a direct parameter of this tool, but can
be verified by calling get_reservation_details"*. The model stated the criterion and
overrode it, so prompt wording has reached its limit there. The tau2 runs therefore use
`review_votes=5` (the default) rather than the calculator e2e's 3: with 40-odd tools there
are many chances to mis-bind, and the relevance vote is what has to reject them.

If votes prove insufficient, the next lever is verification in code rather than more
wording: have create/expand also return **which value** each rule constrains, then check
that the value is a parameter of this tool or a field of its result and drop the item
otherwise. That is the pattern v2 already uses for `system_vars` and `tool_history` — the
model proposes, code verifies. It has to be skipped when a rule constrains an *action*
rather than a value ("confirm before writing" names no parameter), and it correctly keeps
`update_employee.home_address_same_country`, whose `country_code` *is* a parameter.

### Items grounded in nothing are archived

A second defect from the same run: an item cited text from the `AirlineTools` docstring
rather than the policy document. `refmatch` detected it but v2 kept the item, so a rule
nobody wrote reached the spec.

`ground_spec` now archives an item when **none** of its references can be located in the
policy document, with `stage: "refmatch"` and the reason. An item that keeps at least one
grounded quote still survives with its ungrounded ones intact and recorded in
`debug.notes` — dropping those would weaken an otherwise sound item — and an item that
arrived with no references at all is left alone, since `create`/`expand` already refuse to
emit those.

### Where the tests live

| File | Covers | LLM |
|---|---|---|
| `tests/buildtime/gen_spec_v2/test_serialize.py` | byte parity over all 28 fixtures | no |
| `test_sysvars.py` | dict/path loading, shape filtering, rendering, name validation | no |
| `test_tools_input.py` | callables / OpenAPI dict / `list[ToolInfo]` | no |
| `test_context.py` | prompt-slice rendering | no |
| `test_refmatch.py` | grounding, synthetic cases per v1 defect | no |
| `test_refmatch_real_policy.py` | all 95 real references ground to themselves | no |
| `test_reconcile.py` | vote reconciliation, malformed votes | no |
| `test_adapter.py` | `skip` truth table, debug preservation, real corpus | no |
| `test_prompts.py` | every stage sees the inputs it judges against | no |
| `test_stages.py` | the five stages, including misshaped responses | no |
| `test_conflicts.py` | detection bounds, routing to each involved tool | no |
| `test_pipeline.py` | three entry points, per-tool isolation, partial regeneration | no |
| `test_gen_py_contract.py` | identifiers, file collisions, what codegen receives | no |
| `test_examples_only.py` | `generate_guard_examples_v2` rewrites only the examples | no |
| `tests/buildtime/e2e/test_gen_spec_v2_codegen.py` | v2 → adapter → guards that run, for all four tool-input shapes | yes |
| `tests/buildtime/e2e/test_tau2_v2.py` | tau2 airline, simple + complex_api | yes |
| `tests/buildtime/e2e/test_guard_set_delta.py` | reports the v1-vs-v2 guard-set difference (`-m delta`) | yes |

### v1 coverage parity

The e2e files mirror v1's variants one-for-one, and both import v1's
`assert_toolgurards_run`, so the two suites assert identical enforcement rather than
similar-looking enforcement:

| v1 test | v2 counterpart |
|---|---|
| `test_calculator.test_tool_functions_short` / `_long` | `test_gen_spec_v2_codegen.test_tool_functions` |
| `test_calculator.test_tool_methods` | `test_gen_spec_v2_codegen.test_tool_methods` |
| `test_calculator.test_tools_langchain` | `test_gen_spec_v2_codegen.test_tools_langchain` |
| `test_calculator.test_tools_openapi_spec` | `test_gen_spec_v2_codegen.test_tools_openapi_spec` |
| `test_tau2.test_tau2_simple` | `test_tau2_v2.test_tau2_simple` |
| `test_tau2.test_tau2_complex_api` | `test_tau2_v2.test_tau2_complex_api` |
| `generate_guard_examples()` | `generate_guard_examples_v2()` + `test_examples_only.py` |

Two deliberate differences in the tau2 port: item counts are asserted as `>= 1` rather
than `== 1`, because v2 runs an `expand` stage v1's short-options run does not and a
legitimate extra rule must not fail the test; and `complex_api` additionally asserts
that the cancellation rule declares a `tool_history` requirement, which v1's schema
cannot express.

v1's `PolicySpecOptions.spec_steps` phase selection has no v2 equivalent — `SpecV2Options`
exposes `include_examples` and vote counts but not arbitrary stage selection. That is a
deliberate simplification, not an oversight: v2's stages are not independent (triage
depends on enrich, which depends on review's survivors).

The e2e file calls `load_dotenv()` at import, because conftest's autouse fixture loads
`.env` after collection and a `skipif` is evaluated during it.

## Non-goals

`global.json` and orphan-rule items; the rule→items coverage report; a v1→v2 upgrade
function; persisting a user's `skip` decision in a v2 file; a runtime post-invocation
hook; a subject or message-history parameter in generated guards; replacing
`tool_dependencies.py`'s inference with `requires.tool_history`; any change to v1.
