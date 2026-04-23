# Policy Writing Guidelines for ToolGuard

## TL;DR – How to Write a Good Policy Item

A good policy item is:

* ✅ **One rule per paragraph**
* ✅ **Self-contained** (no references)
* ✅ **Specific** (includes numbers and conditions)
* ✅ **Restrictive** (blocks or validates a tool call)
* ✅ **Deterministic** (no human judgment)
* ✅ **Pre-call enforceable only** (checked *before* tool invocation)

**Template:**
`[WHO/WHAT] cannot/can/must [ACTION] [CONDITION/EXCEPTION]`

**Key constraint:**
Policies are evaluated **only before a tool is called**.

* They can **block or validate** a call
* They **cannot force a tool to be called**
* They **cannot run after the tool executes**

**Test:**
Can this be checked *before* calling the tool using available data?
If not → rewrite.

---

## What is a Policy Item?

A **policy item** is a single rule or constraint enforced before a tool is called.

Each policy item should be written as a standalone paragraph that the system will:

1. Extract
2. Match to relevant tools
3. Convert into guard logic

---

## Your Role

You write:

* Clear, complete policy descriptions

The system handles:

* Naming
* Tool assignment
* Code generation

**Focus:** One complete rule per paragraph.

---

## Rules for Writing Policy Items

### 1. Self-contained

* No references to other sections or documents
* No reliance on other policy items

### 2. Specific

* Include all numbers, limits, and conditions
* Avoid vague terms (e.g., "appropriate", "suspicious")

### 3. Restrictive (Enforceable)

* Must block or validate a tool call
* Not just grant permission
* **Must apply before the tool is invoked (never after)**
* **Cannot require forcing a tool call**

### 4. Deterministic

* Must be checkable via logic
* No human judgment or interpretation
* Must rely only on:

  * Tool call parameters
  * Data retrievable via other tools (if available)
* **All required information must be accessible before the tool call**

### 5. Correct Logic

* **AND** → separate policy items
* **OR** → single policy item

---

## Restrictive vs Permissive

Policies must be enforceable *before* a tool call.

✅ **Enforceable (Good):**

```
Customers with "gold" membership get 10% off every flight.
```

→ Must validate the discount before calling the tool

❌ **Not Enforceable (Bad):**

```
Customers with "gold" membership can book any number of passengers.
```

→ No constraint to check

❌ **Also Not Enforceable:**

```
If booking fails, apply a refund.
```

→ Happens after the tool call

❌ **Also Not Enforceable:**

```
If user is eligible, call the booking tool.
```

→ Attempts to force a tool call (not allowed)

**Rule:** Policies only decide whether a tool call is allowed — never whether it must happen, and never what happens after.

---

## AND vs OR Logic

**AND → separate items**

```
Driver must be over 18.
Driver must have passed the theory test.
```

**OR → single item**

```
Allow cancellation if either: (1) within 24 hours OR (2) user has insurance.
```

---

## How to Write a Policy Item

Use a simple, natural sentence:

```
[WHO/WHAT] [CONSTRAINT] [CONDITIONS]
```

### Include:

* Who it applies to (user type, request type)
* The constraint (allowed, prohibited, required)
* Exact conditions (numbers, thresholds, exceptions)


---

## Common Mistakes

| ❌ Bad                    | ✅ Good                                            | Why                 |
| ------------------------ | ------------------------------------------------- | ------------------- |
| Ensure proper validation | Reject if email does not match regex ...              | Too vague           |
| Seems fraudulent         | Reject if price > $10,000 and no verified payment | Not deterministic   |
| Max allowed discount     | Max discount is 50%                               | Missing values      |
| See terms of service     | Full rule written explicitly                      | External dependency |
| Eligible users           | Users with active subscription in last 30 days    | Undefined terms     |

---

## Rewrite Examples

❌ "Ensure discounts are reasonable"
✅ "Discount must not exceed 50% of original price"

---

❌ "Allow flexible cancellations"
✅ "Allow cancellation if within 24 hours OR user has insurance"

---

❌ "Check user eligibility"
✅ "User must have an active subscription paid within the last 30 days"

---

## Examples

### Simple Prohibition

```
Requests to retrieve flight information with a destination of Narnia are not supported.
```

### Conditional Constraint

```
Customers with "regular" membership cannot book more than three passengers unless they have at least 200 frequent flyer points.
```

### Multiple Constraints (AND)

```
Customers with "silver" membership cannot book more than seven passengers.

Customers with "silver" membership cannot book flights if they are blacklisted.
```

### Absolute Prohibition

```
Customers with "banned" status cannot book flights regardless of their points.
```

### Universal Requirement

```
All passengers in a booking must travel in the same cabin class.
```

---

## Final Test

A policy item is valid if:

* Can it be checked BEFORE calling the tool?
* Does it block or validate something?
* Does it include all required values?
* Is all required information available via:

  * Tool parameters, OR
  * Other tools that can be called beforehand?

If any answer is NO → rewrite.
