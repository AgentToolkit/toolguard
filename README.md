# 📦 AI Agents Policy Adherence

This tool analyzes policy documents and generates deterministic Python code to enforce operational policies when invoking AI agent tools.
This work is described in [EMNLP 2025 Towards Enforcing Company Policy Adherence in Agentic Workflows](https://arxiv.org/pdf/2507.16459).

Business policies (or guidelines) are normally detailed in company documents, and have traditionally been hard-coded into automatic assistant platforms. Contemporary agentic approaches take the "best-effort" strategy, where the policies are appended to the agent's system prompt, an inherently non-deterministic approach, that does not scale effectively. Here we propose a deterministic, predictable and interpretable two-phase solution for agentic policy adherence at the tool-level: guards are executed prior to function invocation and raise alerts in case a tool-related policy deem violated.

This component enforces **pre‑tool activation policy constraints**, ensuring that agent decisions comply with business rules **before** modifying system state. This prevents policy violations such as unauthorized tool calls or unsafe parameter values.


**Step 1**:

This component gets a set of tools and a policy document and generated multiple ToolGuard specifications, known as `ToolGuardSpec`s. Each specification is attached to a tool, and it declares a precondition that must apply before invoking the tool. The specification has a `name`, `description`, list of `refernces` to the original policy document, a set of declerative `compliance_examples`, describing test cases that the toolGuard should allow the tool invocation, and `violation_examples`, where the toolGuard should raise an exception.

The specifications are aimed to be used as input into our next component - described below.

The two components are not concatenated by design. As the geneartion involves a non-deterministic language model, the results need to be reviewed by a human. Hence, the output specification files should be reviewed and optionaly edited. For example, removing a wrong compliance example.

The OpenAPI document should describe agent tools and optionally include *read-only* tools that might be used to enforce policies. It’s important that each tool has:
- A proper `operation_id` matching the tool name
- A detailed description
- Clearly defined input parameters and return types
- Well-documented data models

**Step 2**:
Uses the output from Step 1 and the OpenAPI spec to generate Python code that enforces each tool’s policies.

---

## 🐍 Requirements

- Python 3.12+

---

## 🛠 Installation

1. **Clone the repository:**

   ```bash
   uv install toolguard
   ```

4. **Create a `.env` file:**

   Copy the `.env.example` to `src/.env` and fill in your environment variables.
   Replace `AZURE_OPENAI_API_KEY` with your actual API key. and add in TOOLGUARD_GENPY_ARGS your API_KEY.

## ▶️ Usage

```bash
PYTHONPATH=src python -m policy_adherence --policy-path <path_to_policy> --oas <path_to_oas> --out-dir <output_directory> [options]
```

### Arguments

| Argument            | Type     | Description |
|---------------------|----------|-------------|
| `--policy-path`     | `str`    | Path to the policy file. Currently in `markdown` syntax. Example: `/Users/me/airline/wiki.md` |
| `--oas`             | `str`    | Path to an OpenAPI specification file (JSON/YAML) describing the available tools. The `operation_id`s should match tool names. Example: `/Users/me/airline/openapi.json` |
| `--out-dir`         | `str`    | Path to an output folder where the generated artifacts will be written. Example: `/Users/me/airline/outdir2` |
| `--force-step1`     | `flag`   | Force execution of step 1 even if artifacts already exist. Default: `False` |
| `--run-step2`       | `flag`   | Whether to execute step 2. Use `--run-step2` to skip. Default: `True` |
| `--step1-dir-name`  | `str`    | Folder name under the output folder for step 1. Default: `Step1` |
| `--step2-dir-name`  | `str`    | Folder name under the output folder for step 2. Default: `Step2` |
| `--tools`           | `list`   | Optional list of tool names to include. These should be a subset of the OpenAPI `operation_id`s. Example: `--tools create_user delete_user` |

## Example

```bash
PYTHONPATH=src python -m policy_adherence \
  --policy-path ./policy/wiki.md \
  --oas ./spec/openapi.json \
  --out-dir ./output \
  --force-step1 \
  --tools create_user delete_user
```

## Development
`uv pip install .[dev]`
