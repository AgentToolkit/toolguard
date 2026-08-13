# employee_mini — a committed slice of the employee ground truth

The `gen_spec_v2` tests need real generator output to check three things a
synthetic fixture cannot: that the on-disk format round-trips byte for byte,
that references quoted by a model ground back to the policy document they came
from, and that real rule names survive codegen's identifier rules.

The full employee example — 28 specs, the complete policy document and tool
definitions — lives in the **evaluate-toolguard** project, and benchmarking
belongs there. This directory is the minimum slice that keeps those gates
running in a plain `git clone` of toolguard.

## Provenance

Produced from smith's `spec_generation` output for the Enterprise Employee Hub
(`smith/examples/employee/smith/`), with exactly three derivations:

1. **Six of the 28 specs**, chosen for schema coverage (below), each copied
   byte for byte.
2. **`guidance.txt` truncated** to the rules those six specs quote. Seven rule
   bullets nothing references were dropped, along with the
   `## Administrative Actions` heading both of whose rules went. Every rule
   left is one some policy item is grounded in; every kept line is verbatim.
3. **`global.json`'s conflict targets pruned** to the items this subset
   contains. It listed eight items belonging to specs that are not here, which
   would have left the corpus referring to policy items that do not exist.

`system_vars.json` is copied unchanged, including the `action_list` and
`action_description` keys — those are the agent's own action catalog, and
`load_system_vars` excluding them is one of the things tested here.

`tool_definitions.json` is deliberately absent: no test reads it.

## Why these six specs

| Spec | Items | What it is here for |
|---|---:|---|
| `update_employee.json` | 7 | both sides of `skip`: three argument-only rules reach codegen, four need system vars or message history |
| `set_passport.json` | 5 | the `missing_variable` → `missing_var` alias that two real fixtures drifted into |
| `create_time_off_request.json` | 5 | a `post_tool` trigger, and a `missing_tool` pending item |
| `global.json` | 3 | all three pending types, and a `tool_name` with no tool behind it |
| `get_employee.json` | 2 | a spec where everything skips, so nothing reaches codegen |
| `list_employees.json` | 0 | the empty spec — "no rule governs this tool" |

Between them they cover 70 of the 71 distinct key paths in the full 28-spec
corpus. The one absent is a `params` entry inside a `tool_history` record, which
is a free-form dict already exercised by the entries that are here.

## Numbers the tests assert

Change any file here and these move with it:

| Value | Where |
|---|---|
| 6 specs | `test_serialize.py` |
| 27 references, all grounding to themselves | `test_refmatch_real_policy.py` |
| 7 enforceable items across 3 tools | `test_gen_py_contract.py` |
