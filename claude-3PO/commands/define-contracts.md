---
name: define-contracts
description: Phase 6 — Define code contracts (interfaces, types, stubs) from the contracts specification.
argument-hint: <optional-additional-context>
model: sonnet
---

**Phase 6: Define Contracts**

## Workflow

### Step 1: Read Contract Definitions

Read `.claude/contracts/latest-contracts.md` (written during the plan phase) for contract definitions.
The guardrail has already extracted contract names into state.

### Step 2: Write Contract Code Files

Write actual code files that implement the contracts:
- Interfaces, abstract classes, protocols
- Type definitions, type aliases
- Function signatures, stubs
- Data models, schemas

Only code files (valid code extensions) are allowed — the guardrail blocks non-code writes.

### Step 3: Validation

The guardrail validates that all contract names from `latest-contracts.md` appear in the written code files.
The phase completes when:
- At least one code file has been written
- All contract names are found in the written code files

## Constraints

- Only code files can be written (e.g. `.py`, `.ts`, `.go`)
- All contract names from `latest-contracts.md` must appear in the code
- No implementation logic — only signatures, interfaces, and types
