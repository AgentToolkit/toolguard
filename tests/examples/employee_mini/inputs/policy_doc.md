# Employee Hub (mini) — Access-Control Policy

## Context

A cut-down employee directory exposed through an agent: employee records, the
reporting chain, bank accounts, passports, and time-off requests. The server
performs no authorization of its own — this policy is the only enforcement
layer, and it applies based on the acting user's identity and the tool call
being made.

## Actors and Identity

The acting user is described by these system variables:

- `department` — one of `Corporate Leadership`, `Engineering`, `HR`.
- `organization` — one of `IBM Corporation`, `Red Hat`.
- `user_name` — the acting user's display name.
- `user_id` — the acting user's numeric id, matching `employees.user_id`.

Key derived terms:

- **Own data** — the target record's `user_id` equals the acting user's `user_id` (self-service).
- **HR** — the acting user's `department` is `HR`.
- **Direct reports** — the employees whose `manager_id` is the acting user's `user_id`.

## Data Access

- An employee may view and edit only their **own data** — home address, passport, and bank account.
- A `Manager` may view only their **direct reports'** data, in addition to their own.
- **HR** may view and edit all employees' data.
- Users outside the IBM organization are strictly prohibited from viewing IBM employee data.
- An employee's `salary` may be updated only by **HR** or by that employee's **direct manager**.

## Personal-Record Update Rules

- An employee may update a passport **expiration date** only if the new expiration is more than **six months** after the date of the update.
- An employee's passport **issue date** must be strictly earlier than its **expiration date** when both dates are provided in the same call.
- An employee who is on the **blacklist** (persona non grata list) may not update their passport information.

## Data Integrity

- When an employee's **salary** is set or updated, it must be a positive amount (greater than zero).
- An updated employee's work **email** must use their organization's corporate domain: `IBM Corporation` → `@ibm.com`, `Red Hat` → `@redhat.com`. This applies when the organization is provided in the same call.

## Time Off

- An employee may not create a time-off request unless they have sufficient available balance for the requested leave type.
- An employee may create a time-off request only for themselves.
- After an employee creates a time-off request, an email is sent to their manager for approval.
- A single time-off request may not span more than **90 consecutive calendar days** (`end_date` minus `start_date`); longer leave must be split into separate requests.

## Database Writes and Confirmation

- Before performing any action that writes to or modifies the database (create, update, or delete), the agent must first list the details of the action and obtain the user's explicit confirmation ("yes") before proceeding.

## Agent Behavior

- The agent should make only one tool call at a time. When it makes a tool call, it should not respond to the user simultaneously; when it responds to the user, it should not make a tool call at the same time.

## Booking

- A customer with a `regular` membership may not book a flight for more than three passengers unless they own at least 200 frequent flyer points.
