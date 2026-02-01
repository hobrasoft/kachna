# AI Instructions – Functions Directory (Project Kachna)

This document defines **strict rules** for any AI tool generating,
modifying, or reviewing code inside the `functions/` directory.

These rules are **mandatory**.

---

## Purpose of `functions/`

The `functions/` directory contains **executable backend functions**
used by the Kachna system to retrieve **facts** from internal systems
or return **static knowledge**.

These scripts are **not chat prompts**  
and **not UI components**.

They represent the **ground truth layer** of the system.

---

## Fundamental Principles

- Scripts return **facts, not interpretations**
- Scripts are **deterministic**
- Scripts do **not** communicate with LLMs
- Scripts do **not** format human-facing text
- Scripts output **JSON only**

LLMs are allowed to **rephrase results**, never to invent or infer them.

---

## Required Script Interface

Every script **MUST** support two execution modes.

---

### 1. `--describe` mode

Purpose:
- automatic discovery
- database import
- embedding generation
- intent matching

Behavior:
- prints **metadata only**
- outputs **valid JSON**
- performs **no runtime logic**
- does **not** access databases or external systems

Required fields:

```json
{
  "name": "Human readable function name",
  "description": "Short factual description",
  "questions": [
    "Example user question",
    "Another possible phrasing"
  ]
}

