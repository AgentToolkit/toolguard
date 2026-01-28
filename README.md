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
        short=True  # Use short mode for faster generation
    )

    return specs

# Run generation
specs = asyncio.run(generate_specs())
```

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
