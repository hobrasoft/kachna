# AI Instructions – Function Integration (Project Kachna)

This document defines rules for **integrating existing functions**
from the `functions/` directory into the Kachna system.

AI tools must follow these rules when:
- registering functions in the database
- wiring intent detection to functions
- updating metadata
- connecting functions to chat flow

---

## Scope

These rules apply **only to integration logic**.
AI tools **must not implement business logic inside functions**.

Functions are treated as **black boxes**.

---

## Function Discovery

When integrating functions, AI tools MUST:

1. Execute each function with `--describe`
2. Parse returned JSON metadata
3. Use metadata as the **single source of truth**

AI tools MUST NOT:
- infer function purpose from file names
- infer parameters from code
- modify metadata contents

---

## Database Registration

When registering functions in the database, AI tools MUST:

- store function name and description verbatim
- store example questions for embedding generation
- link function path exactly as provided
- mark functions inactive by default unless explicitly enabled

Functions MUST NOT be auto-modified during registration.

---

## Intent Matching

Intent detection MUST:

- be based on embeddings of:
  - user query
  - function questions
- NOT rely on string matching
- NOT rely on file or function names

AI tools MUST NOT invent new example questions.

---

## Execution Rules

When executing a function, AI tools MUST:

1. Select exactly one function
2. Prepare input parameters explicitly
3. Execute the function as a system process
4. Capture STDOUT only
5. Validate output as JSON
6. Reject any non-JSON output

If execution fails, the function must be treated as unavailable.

---

## Output Handling

Function output MUST be treated as **factual data**.

AI tools MUST:
- pass raw JSON to the backend or LLM as facts
- avoid reformatting or summarizing data during integration

Interpretation belongs to the LLM layer only.

---

## Knowledge vs Telemetry

AI tools MUST NOT:
- combine outputs from different function categories
- infer relationships not explicitly encoded

Combination logic must be explicit and deterministic.

---

## Error Handling

Errors returned by functions MUST:
- be passed through unchanged
- NOT be translated into human language at the integration layer

Human-readable error handling belongs to the chat layer.

---

## Stability Rules

AI tools MUST NOT:
- change existing function bindings
- reassign functions to different intents
- alter execution order

Integration changes must be explicit and reviewable.

---

## Core Principle

> **Functions are authoritative. Integration is mechanical.**

Any attempt to "improve" function meaning during integration is a violation.

---

## Final Warning

If an AI tool is unsure how to integrate a function,
it MUST stop and request clarification.

Guessing is forbidden.

