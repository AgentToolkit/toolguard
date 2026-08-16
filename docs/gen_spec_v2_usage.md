# Guard specs v2 — usage

How to drive v2 spec generation from another project (a benchmark repo, an eval
harness), how to hand v2 specs to the v1 code generator, and how the two spec
formats differ.

Everything below imports from `toolguard.buildtime` only. Reaching into
`toolguard.buildtime.gen_spec_v2.*` is never necessary.

## The two formats in one paragraph

v1 (`ToolGuardSpec`) is `{tool_name, policy_items, debug}`, where an item is
`{name, description, references, compliance_examples, violation_examples, skip,
debug}`. v2 (`ToolGuardSpecV2`) is the "step1" format: it adds an `id`, a
`trigger` (`pre_tool` / `post_tool`), a `requires` block saying what the rule
needs in order to be evaluated (`system_vars`, `tool_history`,
`message_history`), open questions in `pending_for_user`, decisions already made
in `resolved_by_user`, per-tool `conflicts`, and a `source_doc` the references
quote verbatim.

## Inputs

| Input | Type | Notes |
|---|---|---|
| `policy_text` | `str` | **Markdown**, not HTML. Rules are found by their `- `/`* ` bullet markers, and every reference must be an exact substring of this text. Passing HTML yields no rules and logs a warning. |
| `tools` | list of callables, or an OpenAPI dict | Same input v1 accepts. Already-parsed `ToolInfo` objects pass through too. |
| `system_vars` | path or dict | The acting user's variables. `action_list` / `action_description` are ignored as non-subject keys. |
| `source_doc` | `str` | Path recorded in each spec, which its references quote. Downstream validators check this path exists. |

## Generate v2 specs

Generation is two phases, so policies and examples can be produced and reviewed
separately.

```python
import asyncio
from toolguard.buildtime import (
    LitellmModel,
    SpecV2Options,
    generate_guard_specs_v2_full,
)

llm = LitellmModel(
    model_name="gpt-4o",
    provider="azure",
    kw_args={"api_base": ..., "api_version": ..., "api_key": ...},  # pragma: allowlist secret
)

specs = asyncio.run(
    generate_guard_specs_v2_full(          # policies AND examples
        policy_text=open("benchmarks/employee/inputs/employee_policy_doc.md").read(),
        tools=ALL_TOOLS,                   # callables, or an OpenAPI dict
        llm=llm,
        work_dir="benchmarks/employee/outputs/<model>/step1_v2",
        system_vars="benchmarks/employee/inputs/system_vars.json",
        source_doc="benchmarks/employee/inputs/employee_policy_doc.md",
        options=SpecV2Options(max_concurrency=4),
    )
)
```

One `<tool_name>.json` is written per tool **that carries at least one rule**; a
tool with nothing to guard gets no file. Rules that were generated and then
dropped are reported in the return value and written to
`<work_dir>/process/rejected.json` — under `process/` so that globbing
`work_dir/*.json` for specs never picks them up.

### Splitting the two phases

`generate_guard_specs_v2` runs policies only. Its output is deliberately **not**
schema-valid, because the step1 schema requires at least one compliance and one
violation example per rule; `generate_guard_examples_v2` fills those in and
rewrites the specs in place.

```python
from toolguard.buildtime import generate_guard_examples_v2, generate_guard_specs_v2

await generate_guard_specs_v2(..., work_dir=out)        # phase 1
await generate_guard_examples_v2(                        # phase 2, later
    tools=ALL_TOOLS,
    specs=out,            # a directory to load from, or a list of specs
    llm=llm,
    work_dir=out,
    system_vars="benchmarks/employee/inputs/system_vars.json",
)
```

### Options

```python
SpecV2Options(
    steps={SpecV2Step.EXPAND, SpecV2Step.REVIEW, SpecV2Step.ENRICH,
           SpecV2Step.EXAMPLES, SpecV2Step.CONFLICTS},  # default: all
    add_iterations=3,      # expand passes; stops early when one adds nothing
    review_votes=5,        # relevance votes per rule
    feasibility_votes=3,   # enrich votes per rule
    max_concurrency=8,     # tools processed at once
)
```

`create` always runs. The entrypoint decides the phase: `generate_guard_specs_v2`
intersects your `steps` with everything-but-`EXAMPLES`.

## Hand v2 specs to the v1 code generator

There is **no conversion step and no second copy of the specs**. A v2 spec file
already loads as a v1 `ToolGuardSpec` — the v1 models ignore the keys they do not
declare. The one thing v1 needs that v2 does not store is `skip`, the flag
`gen_py` uses to leave a rule out of code generation. It is computed in memory:

```python
from toolguard.buildtime import generate_guards_code, to_v1_specs

specs_v1 = to_v1_specs(specs_v2)          # `skip` stamped, nothing else changed

await generate_guards_code(
    tools=ALL_TOOLS,
    tool_specs=specs_v1,
    work_dir="benchmarks/employee/outputs/<model>/step2",
    llm=llm,
    app_name="EmployeeHub",
)
```

`to_v1_spec` handles a single spec. Both leave the v2 objects untouched, and
preserve every v2-only field under the v1 item's free-form
`debug["v2"]` — `id`, `trigger`, `requires`, `pending_for_user`, and
`skip_reasons`.

`generate_guards_code` is v1's own entrypoint and unchanged by any of this; it
also takes `lib_names` (module roots for function-based tools) and `tool_names`
(a subset to generate for). Specs whose every item is skipped contribute no code,
since it drops specs left with no items.

### What `skip` means, and why it is not in the files

`skip_for(item)` is true when generated python guard code could not enforce the
rule, i.e. when the item:

- is not `pre_tool` (it judges the result, not the arguments), or
- needs `message_history` (the conversation), or
- carries any `pending_for_user` entry (the intended behaviour is unsettled), or
- reads any `system_vars` (the acting user's variables).

`tool_history` deliberately does **not** cause a skip: generated guards may call
the application's read-only APIs. `skip_reasons(item)` returns which of the above
applied, for reporting.

The flag is **not written into the spec files**. It answers "should code be
generated for this?", while a consumer reading `skip` from a file may mean "should
this be scored?" — a different question. Everything needed to derive it
(`trigger`, `requires`, `pending_for_user`) is in the file, so any tool can
compute its own view.

## Read and write specs directly

```python
from toolguard.buildtime import ToolGuardSpecV2, dump_spec_v2, load_spec_v2

spec = load_spec_v2("benchmarks/employee/ground_truth/step1/get_bank_account.json")
spec.policy_items = [i for i in spec.policy_items if not i.pending_for_user]
dump_spec_v2(spec, "somewhere/get_bank_account.json")
```

`ToolGuardSpecV2.to_dict()` is the on-disk form — key order and the
omit-when-empty rules the schema requires. Pydantic's `model_dump()` is **not**;
use `to_dict()` or `dump_spec_v2` when writing.

## Running v1 and v2 side by side

Both write `<tool>.json`, so give them separate directories. v1 takes no
`system_vars` and ignores the concept.

```python
from toolguard.buildtime import generate_guard_specs, generate_guard_specs_v2_full

await generate_guard_specs(policy_text=md, tools=ALL_TOOLS, llm=llm,
                           work_dir=out / "step1_v1")
await generate_guard_specs_v2_full(policy_text=md, tools=ALL_TOOLS, llm=llm,
                                   work_dir=out / "step1_v2",
                                   system_vars=sys_vars_path, source_doc=doc_path)
```

Note the markdown requirement: a harness that renders the policy to HTML for v1
must pass **raw markdown** to v2, or v2 extracts no rules at all (and says so in a
warning).

## Failure behaviour

- **One tool's failure is isolated.** It is recorded in the run result's `failed`
  map; every other tool still gets its spec. Nothing raises for a single bad
  response.
- **Rejected rules** land in `process/rejected.json` with the reason and the stage
  that dropped them (`review`, `references`, `examples`).
- A rule whose references cannot be matched to the policy document is dropped
  rather than written with an unquotable reference, since coverage reporting works
  by locating each reference in the document.
