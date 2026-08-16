# gen_spec_v2 — design

Date: 2026-08-13
Status: awaiting review

## Problem

`toolguard.buildtime.gen_spec` turns a policy document plus a set of tools into
one `ToolGuardSpec` JSON file per tool. Its output covers pre-call policy items
only, carries no notion of the acting user's identity, and gives a policy item
no machine-readable statement of what it needs in order to be evaluated.

A newer spec format ("step1") already exists outside this repo, with a published
JSON Schema, a reference corpus, and a validator. It adds a `trigger`
(`pre_tool` / `post_tool`), a `requires` block (system variables, prior tool
calls, conversation history), `pending_for_user` gaps that a human must close,
`resolved_by_user` decisions already made, and per-tool `conflicts`.

A working implementation of the generator lives in smith at
`src/smith/spec_generation`. That folder is being deleted from smith; toolguard
becomes the owner. This design ports the pipeline into toolguard as a sibling of
`gen_spec`, rebuilt on toolguard's own abstractions — `I_TG_LLM` for model
access, `ToolInfo` for tools — and retargeted at the step1 schema, which differs
from smith's output in several material ways (see "Schema deltas"). `gen_spec`
is left untouched.

## Authority and reference material

Repo: `/Users/naamazwerdling/workspace/evaluate-tool-guard`

| What | Path (relative to that repo) |
|---|---|
| **Output contract** | `benchmarks/employee/ground_truth/step1.schema.json` |
| **Cross-file contract** | `eval_scripts/validate_step1_specs.py` |
| **Caller contract** | `eval_scripts/run_step1_v1_v2.py` (`run_v2`, lines 191-207) |
| Prose rationale | `benchmarks/employee/README.md` |
| Reference output — 26 specs, 72 items, 91 references | `benchmarks/employee/ground_truth/step1/` |
| Policy document | `benchmarks/employee/inputs/employee_policy_doc.md` |
| Tools — 33 plain Python callables, `ALL_TOOLS` | `benchmarks/employee/inputs/employee_tools.py` |
| System variables | `benchmarks/employee/inputs/system_vars.json` |

Where this design and those four authorities disagree, they win. All 26
reference specs validate against the schema cleanly (`Draft202012Validator`, 0
errors). The tools are plain functions, so `gen_spec.fn_to_toolinfo` converts
them with no new input format. The benchmark repo is reference material only —
toolguard's tests never read outside the repo (see "Test fixture").

## Decisions taken

| Decision | Choice |
|---|---|
| Output contract | Conform to `step1.schema.json` and to the validator's cross-file rules |
| Spec models | Standalone pydantic models in `gen_spec_v2/data_types.py`; runtime `ToolGuardSpec` / `ToolGuardSpecItem` untouched and unused |
| Conflicts | In scope, including the per-tool split of a cross-tool conflict |
| Global spec / manifest | Out of scope; the schema forbids a global spec outright |
| Ported smith tests | Not ported; new toolguard-native unit tests over pure logic |
| Prompts | Python modules (`SYSTEM` + `user(...)`), not `prompts/*.txt` |
| Pending type spelling | `missing_variable` (schema enum) |
| Bullet splitting | Indented continuation lines join their bullet |
| Empty specs | A tool with no policy items gets no file |
| `requires.system_vars` order | Sorted — canonical and diff-stable; the schema constrains uniqueness, not order |
| Policy document format | **Markdown**, not HTML (see "Policy document format") |
| Rejected items | Returned in the result **and** written to `work_dir/process/rejected.json` |
| Examples | A separate second phase; specs are schema-valid only once it has run |
| Schema in tests | `step1.schema.json` vendored into the test tree; `jsonschema` added as a dev dependency |
| `skip` field | Not emitted; it belongs to a later v2 -> v1 adapter (see "Future work") |
| `tool_enrichment.json` | Not an input (see below) |

### Why `tool_enrichment.json` is not an input

All 26 entries in that file are byte-identical to the `debug.tool_info` blocks
of smith's older ground truth, and those blocks were **LLM-generated**: smith's
`create` prompt asks for `tool_info: {is_read_only, user_enrichment}` and
`run_create` reads it from the response. The file is therefore the ground-truth
run's own generated metadata, extracted verbatim when `debug` was stripped —
not independent human knowledge, despite the README's label. Feeding it back
into generation would hand a scored generator its own prior output for the very
benchmark it is scored on, and v1 (which derives tool metadata itself) would not
get the same help, tilting the v1-vs-v2 comparison.

So the `create` stage derives `is_read_only` / `user_enrichment` itself, uses
them in its own prompts, and drops them — the schema has nowhere to put them.

## Policy document format

`gen_spec_v2` takes the policy document as **markdown text**, not HTML. Three
reasons, all load-bearing:

- Rule extraction is bullet-based; `markdown.markdown(raw)` output has no `- `
  lines at all, so an HTML input would yield **zero** rules.
- The schema's reference contract is verbatim quotes from `source_doc`, and the
  validator opens that path and checks each reference appears in it — i.e.
  against the `.md` file.
- The reference corpus quotes markdown (`**HR** may view and edit all
  employees' data.`). HTML input would produce `<strong>HR</strong> may view…`,
  which matches nothing verbatim and leaves scoring dependent on
  `normalize_ref` stripping tags.

`eval_scripts/run_step1_v1_v2.py`'s `Benchmark.policy_text()` currently returns
`markdown.markdown(raw)` for both versions, so **the runner needs a one-line
change to pass raw text to v2**. To make a mistake here loud rather than silent,
`gen_spec_v2` logs a warning when `policy_document` looks like HTML (contains
`</li>` or `</p>`) and extracts no bullets.

## Public API

The entrypoint names and parameters are fixed by the existing caller in
`run_step1_v1_v2.py`, which already imports them:

```python
from toolguard.buildtime import SpecV2Options, generate_guard_specs_v2_full
```

so wiring into `buildtime.py` and `buildtime/__init__.py`'s `__all__` is part of
this work, not out of scope.

```python
# toolguard/buildtime/buildtime.py — re-exported from toolguard.buildtime

async def generate_guard_specs_v2(
    policy_text: str,                     # markdown
    tools: TOOLS,                         # List[Callable] | OpenAPI dict
    llm: I_TG_LLM,
    work_dir: str | Path,
    *,
    system_vars: str | Path | Dict[str, Any] | None = None,
    source_doc: str = "policy_document",  # path recorded in each spec
    tools2guard: List[str] | None = None,
    options: Optional[SpecV2Options] = None,
) -> List[ToolGuardSpecV2]:
    """Phase 1: policies only. Specs are written without examples and are
    NOT yet schema-valid."""

async def generate_guard_specs_v2_full(...same signature...) -> List[ToolGuardSpecV2]:
    """Phase 1 + phase 2 in one call. Output is schema-valid."""

async def generate_guard_examples_v2(
    tools: TOOLS,
    specs: List[ToolGuardSpecV2] | str | Path,   # objects, or a dir to load
    llm: I_TG_LLM,
    work_dir: str | Path,
    *,
    system_vars: str | Path | Dict[str, Any] | None = None,
    tools2guard: List[str] | None = None,
    options: Optional[SpecV2Options] = None,
) -> List[ToolGuardSpecV2]:
    """Phase 2 alone: fill compliance/violation examples on existing specs and
    rewrite them in place. Mirrors v1's generate_guard_examples."""
```

`system_vars` accepts a path (what the runner passes) or an already-loaded dict;
a path is read and parsed at the edge. `source_doc` must be a real relative path
— the validator checks it exists.

Underneath, the class keeps the shape originally specified:

```python
class SpecV2Step(StrEnum):
    EXPAND, REVIEW, ENRICH, EXAMPLES, CONFLICTS   # create always runs

class SpecV2Options(BaseModel):
    steps: Set[SpecV2Step] = <all>
    add_iterations: int = 3        # expand passes; stops early when a pass adds nothing
    review_votes: int = 5
    feasibility_votes: int = 3     # enrich votes
    max_concurrency: int = 8       # the runner sets this via --v2-concurrency

#: Phase 1 = every step except EXAMPLES. The entrypoints, not the options,
#: decide which phase runs: `generate_guard_specs_v2` intersects the caller's
#: steps with this, `_full` leaves them alone.
PHASE_ONE_STEPS: Set[SpecV2Step]

class ToolGuardSpecGeneratorV2:
    def __init__(
        self,
        llm: I_TG_LLM,
        policy_document: str,
        tools: List[ToolInfo],
        out_dir: Path,
        sys_var: Optional[Union[str, Path, Dict[str, Any]]] = None,
        options: Optional[SpecV2Options] = None,
        source_doc: str = "policy_document",
    ) -> None: ...

    async def generate_policy(self, tool_name: str) -> tuple[List[PolicyItemV2], List[RejectedItem]]
    async def generate_all(self, tools2guard: Optional[List[str]] = None) -> GenerateV2Result
    async def add_examples(self, specs: Sequence[ToolGuardSpecV2]) -> GenerateV2Result
    def load_specs(self) -> List[ToolGuardSpecV2]   # from out_dir, ignoring process/

class GenerateV2Result(BaseModel):
    specs: Dict[str, ToolGuardSpecV2]          # only tools with >= 1 item
    written: List[Path]
    failed: Dict[str, str]                     # tool name -> error string
    rejected: Dict[str, List[RejectedItem]]    # tool name -> dropped items
```

`TOOLS` is converted to `List[ToolInfo]` by calling
`gen_spec.fn_to_toolinfo.function_to_toolInfo` and
`gen_spec.oas_to_toolinfo.openapi_to_toolinfos` directly, so `gen_spec_v2` never
imports `gen_spec.spec_generator`.

## Data model

Standalone pydantic models, field order matching the reference output.
Bracketed keys are conditional.

```
ToolGuardSpecV2   tool_name, source_doc, policy_items[], [conflicts]
  PolicyItemV2    id, name, description, compliance_examples, violation_examples,
                  references, trigger, requires, [pending_for_user], [resolved_by_user]
    Requires      system_vars: List[str]               (always present, may be [])
                  tool_history: List[ToolHistoryEntry] (always present, may be [])
                  message_history: bool                (always present, never null)
    ToolHistory   tool, params: Dict[str, str]
    PendingItem   type, detail, [suggested_source | suggested_tool], question
    ResolvedItem  ... same, plus resolution{answer, decided_by, effect}
  Conflict        id, name, kind, conflicting_policies[], description, question,
                  resolution (always null)
```

`trigger` is `Literal["pre_tool", "post_tool"]`; `kind` is
`Literal["scope", "definition"]`; `decided_by` is `Literal["human"]`.

Conditional-key rules, implemented with an explicit `to_dict()` per class rather
than pydantic's `model_dump` (a blanket `exclude_none` would be wrong — it would
also strip values that must stay, and a `@model_serializer` returning nested
models serializes inconsistently between python and json modes). `to_dict()` is
the on-disk form; `model_dump()` is not:

- `conflicts`, `pending_for_user`, `resolved_by_user` — omitted when empty (the
  schema gives each `minItems: 1`, so an empty array is invalid).
- `suggested_tool` / `suggested_source` — present only for the matching `type`.
- Everything else always present, including empty `system_vars` /
  `tool_history`, `message_history: false`, and `resolution: null` on conflicts.

Item ids are `<tool_name>.<slug>`: the LLM's suffix when it supplied a dotted id,
else a slugified name; collisions get `_2`, `_3`, … `slugify` lowercases and
collapses every non-`[a-z0-9]` run to `_`, satisfying the id pattern.

`data_types.py` also provides `load(path)` / `dump(spec, path)` writing
2-space-indented JSON with a trailing newline and `ensure_ascii=False`.

## Schema deltas from smith's format

Substantive differences between what smith emits and what step1 demands. Each is
a behavior change in the port.

1. **No `debug`.** `debug.tool_info`, `debug.archive`, and `debug.notes` are gone;
   `additionalProperties: false` rejects them. Rejected items move to a run
   report (see "Rejections").
2. **`requires` never uses null.** "Nothing needed" is `tool_history: []` and
   `message_history: false`. Smith's reconciliation produces `None` for both, so
   `reconcile` changes and the models drop `Optional`.
3. **`references` are exact substrings of `source_doc`**, not necessarily whole
   bullets, `minItems: 1`. All 91 reference strings in the corpus are exact
   substrings.
4. **Examples are `minItems: 1`** on both sides — hence the two-phase split.
5. **Conditional companion keys** on pending/resolved entries, enforced by
   `if/then`: `missing_variable` → `suggested_source` required and
   `suggested_tool` forbidden; `missing_tool` → `suggested_tool` required and
   `suggested_source` forbidden; `clarification` → both forbidden.
6. **A cross-tool conflict is split, not dropped.** Every id in
   `conflicting_policies` must resolve within the same file; a conflict spanning
   several tools is "recorded once per affected tool … correlated by a shared id
   slug". The corpus shows `ibm_organization_definition` as 6 per-tool copies.
7. **`Conflict.resolution` is always `null`** (`"type": "null"`). A conflict
   exists only while pending; once decided it is removed and the decision
   recorded as a `resolved_by_user` entry on the affected items.
8. **`kind` is an enum**: `scope` or `definition`.
9. **Id patterns.** `tool_name` matches `^[a-z][a-z0-9_]*$`; item ids
   `^[a-z0-9_]+\.[a-z0-9_]+$` (no dots, dashes, or uppercase in the slug);
   conflict ids `^conflict\.[a-z0-9_]+\.[a-z0-9_]+$`.
10. **`tool_history` param values may be expressions** — the documented forms are
    `input.arguments.<field>`, `input.extensions.subject.<field>`, and
    `year-of(input.arguments.<field>)`. Unknown forms are kept and logged, not
    rejected.
11. **`source_doc` is a path** that must exist.
12. **No global spec, and orphan detection is not the generator's job**: "a rule
    with no tool to attach to is simply absent, and orphan guidance is detected
    by finding policy-document text that no reference quotes."

## Package layout

```
src/toolguard/buildtime/gen_spec_v2/
  __init__.py          public exports
  data_types.py        pydantic spec models + schema-faithful (de)serialization
  inputs.py            policy_document text -> PolicyRule bullets; sys_var -> SystemVars
  context.py           GenContext + render_guidance / render_system_vars / render_tools_*
  spec_generator.py    ToolGuardSpecGeneratorV2 (+ the TOOLS -> ToolInfo conversion)
  conflicts.py         find_conflicts (pairwise, within-tool) + split_and_attach
  refmatch.py          reference repair + exact-substring validation
  utils.py             generate_messages, save helpers
  stages/              create.py, expand.py, review.py, enrich.py, examples.py
  prompts/             create.py, expand.py, review.py, enrich.py, examples.py, conflicts.py
```

Prompts are Python modules rather than `gen_spec`'s `prompts/*.txt` because each
v2 prompt interleaves several rendered blocks — the policy document, system
variables, the tool catalog, the current tool's detail, the item under work — and
string-replace templating fights that. Side benefit: no
`[tool.hatch.build.targets.wheel.sources]` entry is needed, since `.py` files
inside the package ship automatically.

## Pipeline

### Phase 1 — policies

Per tool, bounded by `asyncio.Semaphore(options.max_concurrency)`. One tool's
failure is caught and recorded in `failed`; every other tool still gets a spec.

1. **create** — one LLM call binds policy-document rules to this tool and returns
   draft items plus tool metadata used only in prompts. Items arrive with
   `references` only; examples empty, `trigger` `pre_tool`, `requires` empty
   (`[]`, `[]`, `false`). An item with no reference is not grounded in the
   document and is dropped rather than created.
2. **expand** — up to `add_iterations` further calls, each shown the items so
   far, asking for missed rules. Stops early when a pass adds nothing. Duplicate
   ids and reference-less items are dropped.
3. **review** — `review_votes` concurrent votes per item on relevance and
   validatability. Kept when the mean of `is_relevant AND can_be_validated`
   exceeds 0.5; losers are rejected with the joined vote reasons.
4. **enrich** — `feasibility_votes` concurrent votes per item, reconciled by pure
   logic:
   - `trigger`: majority; a tie (including 0-0) resolves to `pre_tool`.
   - `requires.system_vars`: sorted union, restricted to declared subject
     variables.
   - `requires.tool_history`: the longest vote's list, unless a strict majority
     say empty, in which case `[]`.
   - `requires.message_history`: `True` on a strict majority, else `False`.
   - `references`: union across votes, then intersected with what the item
     arrived with — enrich may only **keep or drop**, never add. If that leaves
     nothing, the original references are restored, so a flaky vote cannot blank
     out a grounded reference.
   - `pending_for_user`: concatenated, deduped by `(type, question)`, then
     normalized (see below).
5. **references** — repair and validate (see below), across all specs.
6. **conflicts** — for each tool with >= 2 items, pairwise upper-triangle calls:
   call `i` compares item `i` against items `i+1..n-1`, keeping every prompt
   small enough that no response truncates mid-JSON. Deduped by id, then split
   per tool (see below).
7. **write** — one `work_dir/<tool_name>.json` per spec **with at least one
   policy item**; a tool with none produces no file. Plus
   `work_dir/process/rejected.json`.

### Phase 2 — examples

`generate_guard_examples_v2` loads the phase-1 specs (or takes them in memory),
and for each item makes one call producing `compliance_examples` and
`violation_examples`, with the system variables rendered so examples use
realistic values, then rewrites each spec in place.

The invariant is enforced at the end of this phase, not before it: an item that
still has an empty side after one retry is rejected rather than written, since
the schema requires at least one of each. Phase-1 output is knowingly
schema-invalid; only post-phase-2 specs are validated.

### Rejections

An item is rejected for reasons the spec format deliberately cannot express:

| # | Reason | Example |
|---|---|---|
| A | Mis-binding — the rule doesn't govern this tool | "Only HR may add a new employee" on `get_passport` |
| B | Orchestration-level — about the agent, not a tool | one-tool-call-at-a-time |
| C | Foreign domain | the flight-booking distractor |
| D | Vacuous permit — nothing to deny | "org chart … may be viewed by any user" |
| E | Nothing worth guarding | `list_employees` exposes no PII or salary |
| F | Duplicate or subsumed by an existing item | a second `edit_own_or_hr` |
| G | A definition, not a rule | "**HR** — the acting user's `department` is `HR`" |

The two cases that look similar but must **not** be rejected are ambiguity
(→ a `clarification` pending, item kept) and a missing signal or tool
(→ `missing_variable` / `missing_tool` pending, item kept). Those are the only
rejection-adjacent reasons the schema can hold.

Rejecting B-E cleanly is load-bearing rather than merely tidy: orphan guidance is
detected by diffing the document against the text references quote, so an item
that quoted the flight-booking bullet would make that bullet look covered. The
README also notes a misattributed distractor is scored as a false positive, so
keeping such items actively hurts.

Rejected items are returned in `GenerateV2Result.rejected` (full item, reason,
stage) and written to **`work_dir/process/rejected.json`** — under `process/`,
never at the top of `work_dir`, because `run_step1_v1_v2.spec_files()` globs
`work_dir/*.json` and would score a stray file there as a bogus tool. v1 already
uses a `process/` subdirectory.

### References

The contract is: every reference is an exact substring of `source_doc`, and every
item has at least one. Per reference, in order:

1. Already a substring, ignoring case → keep the document's own spelling, so a
   quote that only differed in case becomes exact.
2. Otherwise try `gen_spec.utils`'s split heuristic: if the reference splits into
   two halves that each appear verbatim, emit both. This runs **before** snapping:
   two rules quoted as one string are close enough to the first of them to snap,
   and snapping would silently discard the second. A split only succeeds when
   both halves appear verbatim, so it never fires on a mere paraphrase. Its limit
   is that it splits on word boundaries, so two quotes run together with no
   separator fall through to snapping and lose the second.
3. Otherwise snap to the closest document bullet by `difflib.SequenceMatcher`
   ratio on whitespace-stripped, lowercased text; when the best ratio is >= 0.6,
   replace it with that bullet's exact text. Normalization affects only the
   ratio, never what is written back. A bullet's text is itself an exact
   substring, so a successful snap satisfies the contract.
4. Otherwise drop it and log. An item left with zero references is rejected,
   since `references` is `minItems: 1`.

Verified against the real corpus: all 91 references in the 26 reference specs
pass through step 1 unchanged.

Bullet extraction joins indented continuation lines into their bullet — a bullet
absorbs following indented non-bullet lines until a blank line, the next bullet,
or a heading, and logs when it does. Without that, a rule whose substance sits on
a continuation line is silently truncated, which is exactly how smith's older
output produced its one non-verbatim reference.

### Pending normalization

Votes routinely produce pairings the schema forbids, so each entry is normalized
before writing:

- `missing_tool` without a `suggested_tool`, or `missing_variable` without a
  `suggested_source` → coerced to `clarification` with both `suggested_*` keys
  stripped. The generator cannot invent a suggestion it does not have, and
  `clarification` is the type that forbids both.
- Any `suggested_*` key the entry's type forbids is stripped.
- An entry missing `type`, `detail`, or `question` is dropped.

### Conflict splitting

`find_conflicts` returns raw conflicts whose `conflicting_policies` may name
items from more than one tool (detection is within-tool, but the model readily
cites neighbours). For each conflict, with `slug` = the last dotted segment of
its id:

- Drop cited ids that exist in no spec, then group the rest by tool prefix.
- For every tool contributing **>= 2** of its own items, emit one copy with id
  `conflict.<tool>.<slug>`, `conflicting_policies` limited to that tool's items,
  and `resolution: null`, attached to that tool's spec.
- A tool contributing fewer than 2 items is skipped (`minItems: 2`). If no tool
  qualifies, the conflict is dropped and logged.

Applied to the corpus's `ibm_organization_definition`, this yields exactly the 6
per-tool copies it contains.

## System variables

`sys_var` is filtered to subject variables — every key except `action_list` and
`action_description`, which are not policy inputs — and rendered into **every**
stage prompt:

- list-valued entries as allowed-value enums, e.g.
  `- department (input.extensions.subject.department): allowed values = ["Corporate Leadership", "Engineering", "Product", "HR", "Finance"]`
- scalar entries as example values, e.g.
  `- user_id (input.extensions.subject.user_id): example value = 1`

Each variable is tied to `input.extensions.subject.<name>` so the model does not
confuse subject variables with tool arguments; `tool_history[].params` values use
`input.arguments.*`, `input.extensions.subject.*`, or a documented expression
over them. Items record what they read in `requires.system_vars`, and the
validator requires those names to be declared in `system_vars.json` — so an
undeclared name is dropped, and the resulting gap surfaces as a
`missing_variable` pending entry.

`post_tool` rules evaluate against the tool's result. `ToolInfo` carries no
result schema, so prompts expose the return type through `ToolInfo.signature`.

## Validation gate

`step1.schema.json` is vendored into the test tree and `jsonschema` is added as a
dev dependency, so tests assert that generated output satisfies the real
contract. Beyond the schema, the port must satisfy every cross-file rule
`validate_step1_specs.py` enforces:

1. `tool_name` equals the filename stem.
2. `tool_name` is a tool exposed by the tools module.
3. Every policy id is prefixed by the tool name.
4. No duplicate policy ids within a file.
5. Every `requires.system_vars` name is declared in `system_vars.json`.
6. Every `tool_history[].tool` is a known tool.
7. Every conflict id is `conflict.<tool_name>.<slug>`.
8. Every conflict target resolves to an item in the same file.
9. `source_doc` exists as a path.
10. Every reference quotes text present in `source_doc`.

Rules 1-4 and 7-8 hold by construction; 5, 6 and 10 are enforced by the
normalization steps above; 9 is the caller's responsibility via `source_doc`.

## Test fixture

Tests use an in-repo fixture and never read the benchmark repo, so nothing
depends on a path outside toolguard. `tests/examples/employee_mini/`, following
`tests/examples/calculator`:

```
.gitignore                 outputs
__init__.py
inputs/__init__.py
inputs/policy_doc.md       20 bullets distilled from the benchmark's policy document
inputs/tool_functions.py   5 tools as plain functions
inputs/system_vars.json    user_name / user_id / department / organization
                           + action_list / action_description (exercises the filter)
```

Tools: `get_bank_account`, `get_direct_reports`, `update_employee`,
`update_passport`, `create_time_off_request` — plain functions with Google-style
docstrings, verified to convert through the real `function_to_toolInfo`.

Each v2 feature has one carrier in the mini policy:

| Feature | Carrier |
|---|---|
| sys_var scalar | own-data rule -> `user_id` |
| sys_var enum | HR rule -> `department`; corporate-email rule -> `organization` |
| `tool_history` | manager rule -> `get_direct_reports`; outside-IBM rule -> target's organization |
| `message_history` | explicit-`"yes"`-confirmation-before-writes rule |
| `post_tool` | "after an employee creates a time-off request, an email is sent to their manager" |
| `pending_for_user` | blacklist rule (`missing_variable`); leave-balance rule (`missing_tool`) |
| conflict, incl. splitting | `update_employee`: own-data edit vs salary-only-HR-or-manager |
| rejection reasons B-D | one-tool-call-at-a-time; flight-booking bullet; view-by-any-user permit |

## Tests

`tests/buildtime/gen_spec_v2/`, fake LLM, no network:

- **test_data_types.py** — schema fidelity against hand-authored spec objects:
  exact emitted keys and order; `conflicts` / `pending_for_user` /
  `resolved_by_user` absent when empty and present when populated;
  `suggested_source` only for `missing_variable` and `suggested_tool` only for
  `missing_tool`; `requires` emitting `[]` / `[]` / `false` rather than nulls;
  `resolution: null` on conflicts; `load(dump(x)) == x`. Every spec built here is
  also validated against the vendored `step1.schema.json`.
- **test_inputs_context.py** — bullet extraction over
  `employee_mini/inputs/policy_doc.md`: headings and prose dropped, bullets kept
  verbatim with the marker stripped, indented continuation lines joined, a
  warning logged when they are; HTML input yields no bullets and warns;
  `sys_var` filtering drops `action_list` / `action_description`; renderers emit
  enums for lists and example values for scalars.
- **test_voting.py** — enrich `reconcile` (trigger majority and tie ->
  `pre_tool`; sorted sys_vars union; tool_history
  richest-vote-unless-majority-empty; message_history strict majority else
  `False`; references subset-only and never-blank-a-grounded-reference; pending
  dedup) and review `tally`.
- **test_refmatch.py** — an exact-substring reference is untouched; a paraphrase
  snaps to the verbatim bullet; a two-part reference splits; an unmatchable
  reference is dropped and its item rejected when nothing is left.
- **test_pending.py** — normalization: `missing_tool` without `suggested_tool`
  becomes `clarification`; forbidden `suggested_*` keys stripped; incomplete
  entries dropped.
- **test_conflicts.py** — splitting: a conflict citing two tools' items becomes
  one copy per tool with a shared slug and ids rewritten to
  `conflict.<tool>.<slug>`; a tool contributing one item is skipped; a conflict
  with no qualifying tool is dropped; ids existing nowhere are dropped first.
- **test_spec_generator.py** — phase 1 over the mini fixture's 5 tools with a
  scripted fake `I_TG_LLM.chat_json`: stage order, one file written per tool with
  items and none for a tool without, `process/rejected.json` written, one tool's
  failure isolated into `failed` while the others are still written.
- **test_examples_phase.py** — phase 2 over phase-1 output: examples filled,
  specs rewritten in place, an item whose examples stay empty after a retry
  rejected, and the result validated against the vendored schema (the gate that
  phase 1 alone does not pass).

## Feeding v1: no converter, just `skip`

There is no v2 -> v1 adapter, because none is needed. Three findings, each
verified against the real corpus:

1. **A v2 spec file already loads as a v1 `ToolGuardSpec`.** The v1 models set no
   `extra="forbid"`, so pydantic drops `id` / `trigger` / `requires` /
   `source_doc` / `conflicts` / `pending_for_user` / `resolved_by_user` on
   validation. All 26 reference specs load unchanged.
2. **`gen_py` reads only fields v2 already has** — `tool_name`, and per item
   `name` / `description` / `references` / `compliance_examples` /
   `violation_examples` / `skip`.
3. **v2's sentence-style names survive code generation.** All 72 reference names
   convert through `naming_conv.guard_item_fn_name` to valid python identifiers
   with no within-tool collisions (longest 89 characters, which also becomes a
   nested debug directory name — worth remembering on Windows).

So the only missing piece is `skip`, and `gen_spec_v2/v1_compat.py` computes it
**in memory** at hand-over. `skip_for(item)` is true when the item is not
`pre_tool`, needs `message_history`, carries any `pending_for_user`, or reads any
`system_vars`. `tool_history` deliberately does not trigger it: generated guards
may call the application's read-only APIs. `to_v1_spec` / `to_v1_specs` return a
v1 view with `skip` stamped and the v2-only fields preserved under the item's
free-form `debug["v2"]` (including `skip_reasons`, so a skipped rule can be
explained), leaving the v2 objects untouched.

**`skip` is not written into the spec files, deliberately.** The reference
evaluator reads the same field name as "do not score this item", which is a
different question from "do not generate code for this". Applied to the reference
corpus, the predicate marks 57 of 72 items (79%) — leaving 15 of 91 references
visible to a scorer running with its default `skip_history=True`, while v1 (which
emits `skip: false` on every item) and the ground truth keep everything. Storing
the flag would therefore make v1-vs-v2 scoring asymmetric. Keeping it in memory
leaves the scoring question to whoever runs the evaluation.

Mirror tests establish that the v1 path still works when fed by v2:

- **tests/buildtime/gen_spec_v2v1/** — tool parsing is identical to v1's for both
  callables and OpenAPI; a v2-generated spec becomes a valid `ToolGuardSpec`;
  `skip` marks exactly the item v1 codegen cannot enforce; `gen_py`'s own filter
  yields the enforceable subset; names survive identifier conversion; a written
  v2 file loads as v1 with no conversion.
- **tests/runtime/spec_v2v1/** — the runtime loads a result whose specs came from
  v2, and compliant calls pass while violations still raise, reusing the same
  committed calculator guard code and domain as the v1 runtime tests. A skipped
  item changes nothing at guard time, since the runtime executes generated code
  rather than the spec.

Neither mirror asserts anything about generation quality; that belongs in the
evaluate-tool-guard benchmark.

## Out of scope

- A global spec file, `_manifest.json`, and orphan-rule reporting — orphan
  detection is a consumer-side diff of the document against quoted references.
- Any change to `gen_spec`, to the runtime `ToolGuardSpec` models, or to `gen_py`.
- Resolving `pending_for_user` or `conflicts`. The generator only surfaces them;
  `resolved_by_user` and `Resolution` are modelled and loadable so a human or
  another tool can fill them in, but nothing here writes them.
- The one-line change in `eval_scripts/run_step1_v1_v2.py` to pass raw markdown
  to v2. That lives in the benchmark repo.
