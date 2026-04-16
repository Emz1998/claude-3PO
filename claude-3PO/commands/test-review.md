---
name: test-review
description: Phase 6 — Invoke the TestReviewer agent to evaluate test quality and coverage.
argument-hint: <optional-additional-context>
model: sonnet
---

**Phase 6: Test Review**

Invoke 1 `TestReviewer` agent to evaluate the tests written in the previous phase.

## Instructions

1. Launch 1 `TestReviewer` agent with:
   - The test files written in the `/write-tests` phase
   - Instruction to evaluate: correctness, coverage, maintainability, and patterns
   - Must output a verdict of Pass or Fail

## Verdict Format

The `TestReviewer` agent must output a verdict in this format:
```
Verdict: Pass
```
or
```
Verdict: Fail
```

## Evaluation

The guardrail hook parses the reviewer's output:
- **Pass** → tests approved, advance to next phase
- **Fail** → revision needed (sub-phase: `refactor`), then re-review
- Maximum 3 review iterations

## Constraints

- Tests must exist before invoking this phase
- Only edits to existing test files are allowed during the `refactor` sub-phase
