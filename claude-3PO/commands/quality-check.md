---
name: quality-check
description: Phase 8 — Invoke the QASpecialist agent to validate the implementation against acceptance criteria.
argument-hint: <optional-additional-context>
model: sonnet
---

**Phase 8: Quality Check**

Invoke 1 `QASpecialist` agent to validate the implementation.

## Instructions

1. Launch 1 `QASpecialist` agent with:
   - The implementation plan and acceptance criteria
   - The code files written in the `/write-code` phase
   - The test results from the latest test run
   - Instruction to verify: correctness, completeness, edge cases, and acceptance criteria

## Evaluation

The agent validates whether the implementation satisfies all acceptance criteria defined in the plan.

## Constraints

- Code must be written and tests must pass before invoking this phase
- This is a read-only phase — no code modifications allowed
