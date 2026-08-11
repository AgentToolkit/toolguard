# gen_spec_v2 — test baseline

Date: 2026-08-11
Base commit: `e31b21c` (version 0.2.21); the work itself landed as `da24902` on branch `sys_var`
LLM for e2e runs: `claude-sonnet-4-6` via azure
Design: [2026-08-10-gen-spec-v2-design.md](../specs/2026-08-10-gen-spec-v2-design.md)

Written to be re-run and diffed after further benchmarks. Every number was measured, not
inferred; §7 records where a result came from an earlier state of the tree.

## How to reproduce

### Nothing to copy in — the fixtures are committed

Everything below runs from a plain `git clone`. The five tests that need real
generator output read `tests/examples/employee_mini/` — a committed six-spec slice of
smith's employee output, with `guidance.txt` truncated to the rules those specs quote.
No shipped code under `src/` reads any fixture.

The §1 numbers were first measured against the full 28-spec corpus at
`tests/data/specs_v2/`, which is now gitignored and lives in the evaluate-toolguard
project. Both counts are recorded below, with the older one marked as no longer
reproducible from this repo: what changed is the size of the parametrized sets, not
which behaviors are gated.

### Commands

```bash
# No LLM needed. Definitive, ~53s.
PYTHONPATH=tests python -m pytest tests -q --ignore=tests/tmp --ignore=tests/buildtime/e2e

# LLM needed. `PYTHONPATH=tests` is required for the `examples.*` imports.
PYTHONPATH=tests python -m pytest tests/buildtime/e2e/test_gen_spec_v2_codegen.py -q  # 4 tests, ~4 min
PYTHONPATH=tests python -m pytest tests/buildtime/e2e/test_tau2_v2.py -q              # 2 tests, ~4 min
PYTHONPATH=tests python -m pytest tests/buildtime/e2e/test_guard_set_delta.py -q -m delta  # ~1.5 min

# Types. gen_spec_v2 and all new tests must stay at 0.
python -m pyright src/toolguard/buildtime/gen_spec_v2 tests/buildtime/gen_spec_v2
```

## Summary

| Suite | Result | Time |
|---|---|---|
| Non-e2e (unit + contract), committed fixtures | **332 passed**, 0 failed, 0 skipped, 3 pre-existing warnings | 72.2s |
| Non-e2e against the full 28-spec corpus (earlier in session; see §1) | **488 passed**, 0 failed | 52.9s |
| v2 e2e — calculator, 4 tool-input shapes | **4 passed** | in the 417s below |
| v2 e2e — tau2 `simple` | **passed** | " |
| v2 e2e — tau2 `complex_api` | **failed** — transient LLM invalid-JSON, §4 | " |
| v2 e2e combined (6 tests) | **5 passed, 1 failed** | 417.2s |
| v2 e2e — guard-set delta report | **1 passed** | 91.3s |
| v1 e2e — calculator (5) + tau2 (2) | not re-run this session; v1 source untouched | — |
| pyright — `gen_spec_v2` + all new tests | **0 errors** | |
| pyright — whole `src/toolguard` | 15 errors, **all pre-existing** in v1 modules | |

Total: **337 automated checks passing, 1 failing** on committed fixtures alone, the
failure being a transport-level model error rather than a logic defect.

## 1. Non-e2e tests — 332 passed

No LLM. This is the suite to trust for regressions. The `mini` column is what a plain
clone runs — the reproducible number. The `full` column is what these same tests
measured earlier in the session, when they read the 28-spec corpus at
`tests/data/specs_v2/`; reproducing it now means repointing `CORPUS_DIR` in
`tests/buildtime/gen_spec_v2/conftest.py`, since nothing reads that path any more. Only
the four corpus-parametrized files differ between the columns, and only in how many
cases they run — not in which behaviors they gate.

| File | mini | full | Covers |
|---|---:|---:|---|
| `test_stages.py` | 31 | 31 | create/expand/review/enrich/examples, incl. misshaped LLM responses |
| `test_refmatch_real_policy.py` | 28 | 96 | every real reference grounds back to itself (27 vs 95) |
| `test_refmatch.py` | 22 | 22 | grounding: exact, wrapped, markdown-stripped, dash, snap, multi-segment, archive-when-ungrounded |
| `test_reconcile.py` | 19 | 19 | vote reconciliation, malformed votes |
| `test_adapter.py` | 19 | 41 | `skip` truth table, debug preservation, the employee corpus |
| `test_gen_py_contract.py` | 17 | 61 | python identifiers, generated-file collisions, what codegen receives |
| `test_pipeline.py` | 15 | 15 | 3 entry points, per-tool isolation, partial regeneration |
| `test_prompts.py` | 14 | 14 | every stage sees the inputs it judges against |
| `test_sysvars.py` | 13 | 13 | dict/path loading, `action_list`/`action_description` exclusion, nested values kept |
| `test_conflicts.py` | 12 | 12 | detection bounds, routing to each involved tool |
| `test_serialize.py` | 8 | 30 | byte parity against every ground-truth fixture (6 vs 28) |
| `test_examples_only.py` | 8 | 8 | `generate_guard_examples_v2` touches only the examples |
| `test_context.py` | 5 | 5 | prompt-slice rendering |
| `test_tools_input.py` | 5 | 5 | callables / OpenAPI dict / `list[ToolInfo]` |
| **v2 subtotal** | **216** | **372** | |
| pre-existing suite | 116 | 116 | unchanged by this work |

The 3 warnings are pre-existing: one `PytestCollectionWarning` for a test class with
`__init__`, two litellm coroutine warnings.

## 2. v1 coverage parity

Both e2e files import v1's own `assert_toolgurards_run`, so the two suites assert
identical enforcement (5 compliant calls + 5 violations) rather than similar-looking
enforcement.

| v1 test | v2 counterpart | v2 status |
|---|---|---|
| `test_calculator.test_tool_functions_short` / `_long` | `test_gen_spec_v2_codegen.test_tool_functions` | pass |
| `test_calculator.test_tool_methods` | `..._codegen.test_tool_methods` | pass |
| `test_calculator.test_tools_langchain` | `..._codegen.test_tools_langchain` | pass |
| `test_calculator.test_tools_openapi_spec` | `..._codegen.test_tools_openapi_spec` | pass |
| `test_tau2.test_tau2_simple` | `test_tau2_v2.test_tau2_simple` | pass |
| `test_tau2.test_tau2_complex_api` | `test_tau2_v2.test_tau2_complex_api` | fail (§4) |
| `generate_guard_examples()` | `generate_guard_examples_v2()` | pass (8 unit tests) |

Deliberately **not** ported: `PolicySpecOptions.spec_steps` phase selection. v2's stages
are not independent (enrich needs review's survivors; the adapter's `skip` needs enrich's
output), so arbitrary stage selection would silently emit specs whose `requires` and
`trigger` are empty rather than genuinely absent.

## 3. What v2 produces on the employee corpus

From the 28 ground-truth specs through the adapter: **15 of 75 items are codegen-able,
across 7 of 28 tools** — the pure-argument rules (salary positive, email domain, six-month
expiry, issue<expiry, 90-day cap) plus `update_employee.home_address_same_country`, which
needs only a `tool_history` lookup. Everything identity-, conversation-, result-, or
question-dependent is skipped. That is the honest count of what today's runtime can
enforce, and each `skip` condition disappears as the runtime gains that capability.

The committed six-spec slice reproduces the same ratio in miniature: **7 of 22 items
across 3 of 6 tools**, asserted in `test_gen_py_contract.py`. Re-measure the 28-spec
figure in evaluate-toolguard; the mini figure is the one that regresses in CI.

## 4. The one failure, and the variance behind it

`test_tau2_v2.test_tau2_complex_api` failed at `test_tau2_v2.py:99` — the "one spec per
tool" check — because `update_reservation_flights` generation died with *"Exceeded maximum
retries due to invalid JSON format"*. With `on_tool_error="skip"` the pipeline logged it
and returned 13 specs for 14 tools. **This is a transport-level model failure, not a
policy-binding defect.**

Changed after this baseline run: tau2 now passes `on_tool_error="raise"`, so the next run
reports the JSON error directly instead of a confusing count mismatch downstream.

### Over-attachment: real, variance-prone, currently not reproducing

Earlier runs showed v2 binding a rule to tools the policy does not govern. On "Users
cannot book a flight for more than 5 passengers", v1 binds 2 tools:

| Prompt state | `simple` governed tools (want 2) | `complex_api` (want 1) |
|---|---|---|
| Original | 5 | 5 |
| Sharpened prose ("could calling this tool bring it about?") | 3 | 1 ✓ |
| + `review_votes=5` | 3 | 2 ✗ regressed |
| Current tree (this baseline) | **2 ✓** | not reached (§4) |

The residual offender was `update_reservation_flights`, signature
`(reservation_id, cabin, flights, payment_id)` — no passenger parameter. Its generated item
said so itself: *"The passenger count is not a direct parameter of this tool, but can be
verified by calling get_reservation_details"* — then bound anyway.

It did **not** reproduce in this baseline run. Treat it as latent rather than fixed: it
appeared in three runs and vanished in the fourth, and `review_votes=5` made `complex_api`
worse while the runs contradicted each other. That pattern is sampling variance, not a
threshold, so a re-run may show it again.

A guard from such a binding would deny legitimate flight changes on any reservation
already over 5 passengers — worse than a missing guard.

**Untried lever if it recurs:** have create/expand also return which value each rule
constrains, then verify in code that it is a parameter of this tool or a field of its
result — the pattern v2 already uses for `system_vars` and `tool_history`. Must be skipped
when a rule constrains an action rather than a value, and it correctly keeps
`update_employee.home_address_same_country` (`country_code` *is* a parameter). An
output-field version of this was written and **reverted** on request; the criterion now
lives in prose only.

**Fixed and verified:** items citing text outside the policy document. One item quoted the
`AirlineTools` docstring; `ground_spec` now archives an item when none of its references
can be located in the policy document (`stage: "refmatch"`). Confirmed archived in both
tau2 variants.

## 5. Guard-set delta, v1 vs v2-via-adapter

Calculator policy, both generators at full settings, re-measured for this baseline.

```
| Tool            | v1 | v2 | v1 only | v2 only |
| add_tool        | 1  | 1  |    —    |    —    |
| divide_tool     | 1  | 1  |    —    |    —    |
| map_kdi_number  | 0  | 0  |    —    |    —    |
| multiply_tool   | 1  | 1  |    —    |    —    |
| subtract_tool   | 0  | 0  |    —    |    —    |
Totals: v1 3 — v2 3 — v2 captured but not enforceable: 1
```

**No guard is lost by switching to v2**, and v2 additionally captured a rule v1 dropped
entirely: `map_kdi_number`'s "KDI 6.28 blocks multiplication", recorded as `post_tool`.
This confirms the expectation that once v2's unenforceable items are skipped, the remaining
set matches v1 — on this policy, exactly.

Report is written to `tests/tmp/e2e/guard_set_delta/guard_set_delta.md` on each run.

## 6. Not covered

- v1's own 7 e2e tests were not re-run this session. v1 source is untouched, so they
  should be unaffected — an inference, not a measurement.
- No runtime post-invocation path, no subject or message-history parameter in generated
  guards; those are what the four `skip` conditions stand in for.
- `global.json`, orphan-rule items, and the rule→items coverage report: out of scope by
  decision.
- v1→v2 spec upgrade, and persisting a user's `skip` choice in a v2 file: out of scope by
  decision.
- Prompt-response field structures are frozen; changes require explicit approval.

## 7. Caveats on provenance

- The 417s e2e run is the authoritative baseline for the current tree, with one exception:
  the `on_tool_error="raise"` change to tau2 was made **after** it, so tau2's next run will
  report a model failure differently (more clearly) than this one did.
- The four calculator variants were also measured at 248s against the sharpened-prose
  prompts before the reverted field experiment; the 417s run re-confirms them on the
  current tree.
- `test_guard_set_delta.py` passed, after which its renderer was edited to match rules by
  slug and left `slugify` unimported — a `NameError` pyright caught. Fixed, and the 91s
  re-run above is post-fix.
- tau2 uses `review_votes=5`; the calculator e2e uses 3. Both use `add_iterations=1` and
  `example_number=2` for speed, not generation quality. Comparing future runs is only
  meaningful at the same settings.
- Prompt files are `lru_cache`d per process, so a prompt edited while a run is in flight
  does not take effect mid-run.
- e2e results depend on the model. Record `MODEL_NAME` alongside any future comparison.
- §1's per-file counts were measured twice: the `full` column against the 28-spec corpus
  in place, the `mini` column after it was replaced by
  `tests/examples/employee_mini/`. The `mini` column is the one CI will reproduce.
