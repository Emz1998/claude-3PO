---
name: write-code
description: Phase 6 — Write minimal implementation code to pass the failing tests (or implement the plan directly if TDD=false).
argument-hint: <optional-additional-context>
model: sonnet
---

**Phase 6: Write Implementation Code**

Write the minimal code needed to satisfy the implementation plan and (if TDD=true) pass the failing tests.

## Instructions

1. If `TDD=true`: read the failing tests written in the `/write-tests` phase. Write only enough code to make them pass.
2. If `TDD=false`: follow the approved implementation plan from the `/plan` phase directly.
3. Do not over-engineer. Implement only what is required by the plan and tests.
4. Run tests after implementation to confirm all pass.

## Constraints

- No agents are launched in this phase — the main agent writes the code directly
- Follow the implementation plan strictly
- Do not add features or logic beyond what the plan specifies
- Commit changes when done
