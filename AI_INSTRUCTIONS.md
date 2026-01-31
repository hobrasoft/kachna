# AI Instructions – Project Kachna

These rules MUST be followed by any AI tool generating or modifying code
in this repository.

## General
- Do NOT introduce new dependencies without explicit instruction
- Prefer explicit, readable code over clever abstractions
- Do NOT invent configuration options

## Backend (FastAPI)
- Pydantic models MUST be explicit, no implicit dicts
- async code ONLY where required
- Configuration MUST be read from INI files, never hardcoded

## Frontend (React)
- No business logic in UI components
- API access MUST go through a single client module
- No direct fetch calls inside components
- Errors MUST be user-visible and non-blocking

## API Compatibility
- MUST remain compatible with OpenAI `/v1/models` and `/v1/chat/completions`
- No breaking changes without version bump

## Database Access Rules (MANDATORY)

- ALL database access MUST go through the `Database` class.
- ALL SQL queries (SELECT, INSERT, UPDATE, DELETE, DDL, functions, procedures)
  MUST be defined and executed exclusively inside the `Database` class.
- SQL MUST NOT appear in any other file in this repository.
- The `Database` class MUST NOT be bypassed, even for simple queries.
- Convenience or performance is NOT a valid reason to use SQL elsewhere.

Forbidden outside `Database`:
- Raw SQL strings
- ORM queries
- Query builders
- Embedded SQL in services, routers, or business logic

Allowed outside `Database`:
- Calling public methods of the `Database` class only

The `Database` class is the single source of truth for:
- SQL queries
- Database schema interaction
- Connection handling
- Transactions

Violations of this rule are considered a critical architecture bug.

