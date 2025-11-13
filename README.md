# 📦 AI Agents Policy Adherence

This tool analyzes policy documents and generates deterministic Python code to enforce operational policies when invoking AI agent tools.

## 🚀 Features

The workflow consists of two main steps:

**Step 1**:  
Takes a policy document in Markdown format and an OpenAPI specification describing the available tools. For each tool, it generates a JSON file containing associated policies and examples of both compliance and violations.  
These files can be reviewed and edited manually before proceeding to Step 2.  
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
- `pip`

---

## 🛠 Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.ibm.com/MLT/gen_policy_validator.git
   cd gen_policy_validator
   ```

2. **(Optional) Create and activate a virtual environment:**

   ```bash
   python3.12 -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```
[.env.example](.env.example)
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