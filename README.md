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

- Python 3.10+

---

## 🛠 Installation

1. **Clone the repository:**

   ```bash
   uv pip install toolguard
   ```


## 📚 Usage Examples

### Quick Start

ToolGuard provides two main APIs:

1. **Buildtime API** (`toolguard.buildtime`): Generate guard specifications and code
2. **Runtime API** (`toolguard.runtime`): Execute guards during tool invocation

### Complete Example: Calculator with Policy Guards

This example demonstrates how to enforce policies on calculator tools.

#### Step 1: Define Your Tools

```python
# tools.py
def divide_tool(g: float, h: float) -> float:
    """Divides one number by another."""
    return g / h

def add_tool(a: float, b: float) -> float:
    """Adds two numbers."""
    return a + b

def multiply_tool(a: float, b: float) -> float:
    """Multiplies two numbers."""
    return a * b

def map_kdi_number(i: float) -> float:
    """Maps a number to its KDI value."""
    return 3.14 * i
```

#### Step 2: Define Your Policy Document

```markdown
# Calculator Usage Policy

## Operation Constraints

- **Division by Zero is Not Allowed**
  The calculator must not allow division by zero.

- **Summing Numbers Whose Product is 365 is Not Allowed**
  The calculator must not allow addition if their product equals 365.
  For example, adding 5 + 73 should be disallowed (5 * 73 = 365).

- **Multiplying Numbers When Any Operand's KDI Value Equals 6.28 is Not Allowed**
  If any operand has KDI(x) = 6.28, multiplication must be rejected.
```

#### Step 3: Generate Guard Specifications (Buildtime)

```python
import asyncio
from pathlib import Path
from toolguard.buildtime import generate_guard_specs, LitellmModel

async def generate_specs():
    # Configure LLM
    llm = LitellmModel(
        model_name="gpt-4o",
        provider="azure",
        kw_args={
            "api_base": "your-api-base",
            "api_version": "2024-08-01-preview",
            "api_key": "your-api-key", # pragma: allowlist secret
        }
    )

    # Load policy text
    with open("policy.md", "r") as f:
        policy_text = f.read()

    # Define tools
    tools = [divide_tool, add_tool, multiply_tool, map_kdi_number]

    # Generate specifications
    specs = await generate_guard_specs(
        policy_text=policy_text,
        tools=tools,
        work_dir="output/step1",
        llm=llm,
        options=PolicySpecOptions(spec_steps={PolicySpecStep.CREATE_POLICIES},) # Use short mode for faster generation
    )

    return specs

# Run generation
specs = asyncio.run(generate_specs())
```

##### Controlling Specification Generation
generate_guard_specs now accepts a PolicySpecOptions object that controls how specifications are generated.
```python
from toolguard.buildtime import PolicySpecOptions, PolicySpecStep

options = PolicySpecOptions(
    spec_steps={
        PolicySpecStep.CREATE_POLICIES,
        PolicySpecStep.ADD_POLICIES,
        PolicySpecStep.REVIEW_POLICIES
    },
    add_iterations=2,
    example_number=3
)
```


###### Parameters

| Parameter        | Description                                                                                                                      |
|------------------|----------------------------------------------------------------------------------------------------------------------------------|
| `spec_steps`     | Which generation phases to run. Defaults to **all steps**. (see available steps below).                                                                       |
| `add_iterations` | How many refinement passes to run when adding policies. Default is `3`.                                                          |
| `example_number` | Controls how many examples are generated per policy:<br>• `None` = model decides<br>• `0` = no examples<br>• `>0` = exact number |

###### Available `PolicySpecStep` Values

The following generation phases can be selected via `spec_steps`:

- `CREATE_POLICIES` – Extract initial policy specifications from the policy document.
- `ADD_POLICIES` – Iteratively refine and extend generated policies.
- `REVIEW_POLICIES` – Review generated policies for correctness.
- `CORRECT_REFERENCES` – Ensure references correctly map to the original policy document.
- `REVIEW_POLICIES_SELF_CONTAINED` – Ensure each policy description is fully self-contained and unambiguous.
- `REVIEW_POLICIES_FEASIBILITY` – Validate that each policy can be deterministically enforced.

##### Alternative: v2 Specification Generation

`gen_spec_v2` is a second, parallel generator. Where the generator above records a
rule's text and examples, v2 also records **who** is acting, **when** the rule applies,
**what else** is needed to decide it, and **what is missing** to enforce it at all — so
rules that today's generator silently drops become visible instead.

It is an alternative, not a replacement: `generate_guard_specs` is unchanged and remains
the default.

```python
from toolguard.buildtime import (
    generate_guard_specs_v2_full,
    specs_v2_to_v1,
    generate_guards_code,
)

specs = await generate_guard_specs_v2_full(
    policy_text=policy_text,          # raw markdown; no bullet structure required
    tools=tools,                      # functions, an OpenAPI dict, or a list[ToolInfo]
    llm=llm,
    work_dir="specs_v2",              # give v2 its own directory (see the note below)
    system_vars="sys_var.json",        # a dict or a path; optional
    source_doc="policy_doc.md",
)

# Feed the existing code generator:
v1_specs = specs_v2_to_v1(specs, known_tools=[t.__name__ for t in tools])
guards = await generate_guards_code(
    tool_specs=v1_specs, tools=tools, work_dir="code", llm=llm, app_name="myapp"
)
```

###### System variables

`system_vars` declares the attributes of the acting user that policies may refer to,
which is what makes rules like "only HR may add an employee" expressible. Pass a dict or
a path to a JSON file:

```json
{
  "user_name": "Bob",
  "user_id": 1,
  "department": ["Corporate Leadership", "Engineering", "Product", "HR", "Finance"],
  "organization": ["IBM Corporation", "Red Hat", "Kyndryl"]
}
```

A list value is a closed set of allowed values; anything else is one example of the shape
to expect. Nested values are fine — a structured attribute of the acting user is still a
subject variable. Two keys are ignored if present, `action_list` and
`action_description`, because they describe the agent's own tools rather than the acting
user. Generated specs may only name variables declared here.

###### What each policy item records

| Field | Meaning |
|---|---|
| `trigger` | `pre_tool` (decided from the arguments) or `post_tool` (decided against the result) |
| `requires.system_vars` | Which acting-user attributes the rule reads |
| `requires.tool_history` | A tool that must be called first, and with which arguments |
| `requires.message_history` | The rule can only be decided from the conversation |
| `pending_for_user` | A `missing_tool`, `missing_var`, or `clarification` gap, with the question to ask |
| `references` | Verbatim spans of the policy document the rule came from |

###### Entry points

| Function | Does |
|---|---|
| `generate_guard_specs_v2` | One spec per tool → `<tool>.json`. No cross-tool work. |
| `generate_spec_conflicts_v2` | Finds conflicts across a complete spec set (loaded from `work_dir` if not passed) and records them on each spec. Idempotent. |
| `generate_guard_specs_v2_full` | All tools, then conflicts — one call for a full build. |
| `generate_guard_examples_v2` | Reruns only the examples stage for specs already on disk, leaving everything else on each item untouched (the v2 counterpart of `generate_guard_examples`). |

`SpecV2Options` controls `review_votes` (5), `enrich_votes` (3), `add_iterations` (3),
`include_examples`, `example_number`, `max_concurrency` (8), and `on_tool_error`
(`"skip"` by default, so one tool's failure does not abort the run).

###### Feeding the code generator

`specs_v2_to_v1` marks an item `skip=True` when today's codegen and runtime cannot
enforce it *correctly* — generated guards receive `args` + `api` only, with no acting
user and no conversation, and there is no post-invocation hook. So an item is skipped
when it has a `pending_for_user` gap, needs `message_history`, is `post_tool`, or reads
`system_vars`. Expect a v2 run over an identity-heavy policy to yield few guards; that
is the honest count of what can be enforced today, and each condition disappears as the
runtime gains the corresponding capability.

> **Point v2 at its own `work_dir`.** v2 writes `<tool>.json`, the same filenames v1
> uses, and v1's loader accepts a v2 file while ignoring its extra fields — which would
> leave every item `skip=False` and generate guards for rules that cannot be enforced.

#### Step 4: Generate Guard Code (Buildtime)

```python
from toolguard.buildtime import generate_guards_code

async def generate_code():
    # Use specs from Step 3
    guards = await generate_guards_code(
        tool_specs=specs,
        tools=tools,
        work_dir="output/step2",
        llm=llm,
        app_name="calculator"
    )

    return guards

# Run code generation
guards = asyncio.run(generate_code())
```

#### Step 5: Use Guards at Runtime

```python
from toolguard.runtime import (
    load_toolguards,
    ToolFunctionsInvoker,
    PolicyViolationException
)

# Load generated guards
with load_toolguards("output/step2") as toolguard:
    # Create tool invoker
    invoker = ToolFunctionsInvoker([divide_tool, add_tool, multiply_tool])

    # Valid calls - these will succeed
    await toolguard.guard_toolcall("add_tool", {"a": 5, "b": 4}, invoker)
    await toolguard.guard_toolcall("divide_tool", {"g": 10, "h": 2}, invoker)

    # Policy violations - these will raise exceptions
    try:
        # Division by zero
        await toolguard.guard_toolcall("divide_tool", {"g": 5, "h": 0}, invoker)
    except PolicyViolationException as e:
        print(f"Policy violation: {e}")

    try:
        # Product equals 365
        await toolguard.guard_toolcall("add_tool", {"a": 5, "b": 73}, invoker)
    except PolicyViolationException as e:
        print(f"Policy violation: {e}")
```

### Working with Different Tool Types

#### Python Functions

```python
from toolguard.runtime import ToolFunctionsInvoker

tools = [divide_tool, add_tool, multiply_tool]
invoker = ToolFunctionsInvoker(tools)
```

#### Class Methods

```python
from toolguard.runtime import ToolMethodsInvoker
from toolguard.extra.api_to_functions import api_cls_to_functions

class CalculatorTools:
    def divide_tool(self, g: float, h: float) -> float:
        return g / h

    def add_tool(self, a: float, b: float) -> float:
        return a + b

# Convert class methods to functions for spec generation
tools = api_cls_to_functions(CalculatorTools)

# Use at runtime
invoker = ToolMethodsInvoker(CalculatorTools())
```

#### LangChain Tools

```python
from langchain.tools import tool
from toolguard.runtime import LangchainToolInvoker
from toolguard.extra.langchain_to_oas import langchain_tools_to_openapi

@tool
def divide_tool(g: float, h: float) -> float:
    """Divides one number by another."""
    return g / h

tools = [divide_tool, add_tool]

# Convert to OpenAPI for spec generation
oas = langchain_tools_to_openapi(tools)

# Use at runtime (note: args wrapped in "args" key)
invoker = LangchainToolInvoker(tools)
await toolguard.guard_toolcall("divide_tool", {"args": {"g": 5, "h": 2}}, invoker)
```

#### OpenAPI Specification

```python
from toolguard.buildtime.utils.open_api import OpenAPI

# Load OpenAPI spec
oas = OpenAPI.load_from("calculator_api.json")

# Generate guards using OpenAPI
guards = await generate_guards_code(
    tool_specs=specs,
    tools=oas.model_dump(),
    work_dir="output/step2",
    llm=llm,
    app_name="calculator"
)
```


#### MCP Server Tools
```python
import asyncio
from fastmcp.client import Client, StreamableHttpTransport
from toolguard.extra.mcp_tools_to_oas import list_mcp_tools, mcp_tools_to_openapi

async def export_mcp_tools():
    # Create HTTP transport for MCP server
    transport = StreamableHttpTransport(url="http://127.0.0.1:8765/mcp")
    mcp_client = Client(transport)

    # List tools from MCP server
    tools = await list_mcp_tools(mcp_client)

    # Convert to OpenAPI spec
    openapi_spec = mcp_tools_to_openapi(
        tools,
        title="My MCP Tools",
        version="1.0.0"
    )
    return openapi_spec

# Run the async function
openapi_spec = asyncio.run(export_mcp_tools())
```

### Advanced Configuration

#### Selective Tool Guard Generation

```python
# Generate specs only for specific tools
specs = await generate_guard_specs(
    policy_text=policy_text,
    tools=tools,
    work_dir="output/step1",
    llm=llm,
    tools2guard=["divide_tool", "add_tool"]  # Only these tools
)

# Generate code only for specific tools
guards = await generate_guards_code(
    tool_specs=specs,
    tools=tools,
    work_dir="output/step2",
    llm=llm,
    app_name="calculator",
    tool_names=["divide_tool"]  # Only this tool
)
```

#### Custom LLM Configuration

```python
from toolguard.buildtime import LitellmModel

# Azure OpenAI
llm = LitellmModel(
    model_name="gpt-4o-2024-08-06",
    provider="azure",
    kw_args={
        "api_base": "https://your-resource.openai.azure.com",
        "api_version": "2024-08-01-preview",
        "api_key": "your-key" # pragma: allowlist secret
    }
)

# OpenAI
llm = LitellmModel(
    model_name="gpt-4o",
    provider="openai",
    kw_args={"api_key": "your-key"} # pragma: allowlist secret
)

# Anthropic
llm = LitellmModel(
    model_name="claude-3-5-sonnet-20241022",
    provider="anthropic",
    kw_args={"api_key": "your-key"} #pragma: allowlist secret
)
```

### Loading Previously Generated Guards

```python
from toolguard.runtime import load_toolguards, ToolGuardsCodeGenerationResult

# Load from default location
with load_toolguards("output/step2") as toolguard:
    await toolguard.guard_toolcall("add_tool", {"a": 1, "b": 2}, invoker)

# Load from custom file
result = ToolGuardsCodeGenerationResult.load("output/step2", "custom_results.json")
```

### Error Handling

```python
from toolguard.runtime import PolicyViolationException

try:
    await toolguard.guard_toolcall("divide_tool", {"g": 5, "h": 0}, invoker)
except PolicyViolationException as e:
    # Handle policy violation
    print(f"Policy violated: {e}")
    # Log the violation, notify admin, etc.
except Exception as e:
    # Handle other errors
    print(f"Unexpected error: {e}")
```

---

## 🔍 How It Works

1. **Specification Generation**: Analyzes policy documents and tools to create `ToolGuardSpec` objects with compliance/violation examples
2. **Code Generation**: Converts specifications into executable Python guard functions with tests
3. **Runtime Enforcement**: Guards are executed before tool invocation, raising `PolicyViolationException` if policies are violated

---

## 📖 API Reference

### Buildtime API

- `generate_guard_specs()`: Generate guard specifications from policy text
- `generate_guards_code()`: Generate executable guard code from specifications
- `LitellmModel`: LLM configuration for various providers

v2 specification generation (alternative to `generate_guard_specs`):

- `generate_guard_specs_v2()`: Generate v2 specs, one per tool
- `generate_spec_conflicts_v2()`: Record conflicts across a complete spec set
- `generate_guard_specs_v2_full()`: Both of the above, in one call
- `specs_v2_to_v1()` / `spec_v2_to_v1()`: Convert v2 specs for `generate_guards_code()`
- `SpecV2Options`: Vote counts, iterations, concurrency, error policy

### Runtime API

- `load_toolguards()`: Load generated guards for runtime use
- `ToolguardRuntime.guard_toolcall()`: Execute guard before tool invocation
- `ToolFunctionsInvoker`: Invoker for Python functions
- `ToolMethodsInvoker`: Invoker for class methods
- `LangchainToolInvoker`: Invoker for LangChain tools
- `PolicyViolationException`: Raised when a policy is violated

---

## Development
`uv pip install .[dev]`
