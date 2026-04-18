# Mock Plan — Example Gadget Refactor

## Context

This is a mock plan used as a placeholder/example. The "Gadget" subsystem is fictional — no real files in this repo are changed by this plan.

## Approach — 3 staged steps

### Stage 1 — Extract pure helpers

Pull duplicated `format_gadget()` calls into a new `lib/gadget_format.py`.

- **Touch**: new `lib/gadget_format.py`; `tests/test_gadget_format.py`.
- **TDD**: parametrized tests for empty / single / multi gadget cases first.
- **Risk**: callers may pass slightly different shapes — diff before unifying.

### Stage 2 — Centralize gadget constants

Move `GADGET_LIMIT`, `GADGET_TIMEOUT`, and the `"## Gadgets"` marker into `constants/gadgets.py`.

- **Touch**: new `constants/gadgets.py`; revise importers.
- **TDD**: revise existing tests to import from the new location.
- **Risk**: missed import sites — grep before merging.

### Stage 3 — Slim long gadget functions

Split any function over 15 lines in `gadget_processor.py` into focused helpers.

- **TDD**: micro-tests per extracted helper.
- **Verification**: AST lint asserting max 15 lines per `FunctionDef`.

## Critical files

- `lib/gadget_format.py` (new, stage 1)
- `constants/gadgets.py` (new, stage 2)
- `gadget_processor.py` (stage 3)

## Verification plan

1. `python3 -m pytest` — full suite green at each stage.
2. Grep invariants — one `format_gadget` definition, one `GADGET_LIMIT` constant.
3. Smoke run on a sample gadget input.

## Out of scope

- Rewriting the gadget storage layer.
- Migrating gadget models to Pydantic.
