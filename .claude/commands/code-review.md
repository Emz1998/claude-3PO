---
name: code-review
description: Phase 9 — Invoke the CodeReviewer agent to review code quality and correctness.
argument-hint: <optional-additional-context>
model: sonnet
---

**Phase 9: Code Review**

Invoke 1 `CodeReviewer` agent to review the implementation code.

## Instructions

1. Launch 1 `CodeReviewer` agent with:
   - The code files written in the `/write-code` phase
   - The implementation plan for context
   - Instruction to evaluate: correctness, bugs, security, readability, and best practices
   - Must output confidence and quality scores

## Score Format

The `CodeReviewer` agent must output scores in this format:
```
Confidence Score: [0-100]
Quality Score: [0-100]
```

## Evaluation

The guardrail hook parses the reviewer's output:
- **Both scores >= 80** → code approved, advance to next phase
- **Any score < 80** → revision needed (sub-phase: `refactor`), then re-review
- Maximum 3 review iterations

## Constraints

- Code must be written before invoking this phase
- Only edits to existing code files are allowed during the `refactor` sub-phase
