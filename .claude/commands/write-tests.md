---
name: write-tests
description: Phase 5 (TDD) — Write failing tests using test-engineer, then review with test-reviewer. Only runs when TDD=true.
argument-hint: <optional-additional-context>
model: sonnet
---

**Phase 5: Write Failing Tests (TDD Red Phase)**

> This phase only executes when `TDD=true`. If TDD is disabled, this phase is skipped.

## Workflow

### Step 1: Write Failing Tests
Invoke 1 `test-engineer` agent with:
- The approved implementation plan from the `/plan` phase
- Instruction to write failing tests ONLY — no implementation code
- Tests should cover all acceptance criteria

### Step 2: Review Tests
Invoke 1 `test-reviewer` agent with:
- The tests written by `test-engineer`
- Instruction to review for: correctness, coverage adequacy, readability/maintainability
- Score: **Confidence Score** (0-100) and **Quality Score** (0-100)
- Threshold: both scores must be >= 80 to pass

### Step 3: Evaluate Result
The guardrail hook parses the reviewer's output:
- **Both scores >= 80** → tests approved, advance to `/write-code`
- **Any score < 80** → revision needed, repeat from Step 1 (up to 3 iterations)

## Review Format

The `test-reviewer` must output scores in this format:
```
Confidence Score: [0-100]
Quality Score: [0-100]
```

## Constraints

- Tests must be failing (no implementation yet)
- Do not write any production code in this phase
- Maximum 3 iterations
- Pass revision feedback to the next test-engineer iteration
