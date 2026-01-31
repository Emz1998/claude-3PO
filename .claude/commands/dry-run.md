---
name: dry-run
description: Dry run the /implement workflow to test guardrail enforcement
argument-hint: <milestone-id> [tdd|ta|default]
model: opus
---

## Instructions

- This is a **test run** for the /implement workflow guardrail
- Verify guardrail blocks out-of-order subagent calls
- Proceed until the end unless a guardrail fully blocks you.
- If you need help, stop and ask user for help

## Workflow Test Sequence

Trigger the following sequence of transitions with Skill tool.

`explore` → `plan` → `plan-consult` → `finalize-plan` → `write-test` → `review-test` → `write-code` → `code-review` → `refactor` → `validate` → `commit`

## Prohibited Actions

- Do not make code changes
- Do not create commits
- Do not manually edit cache to fake transitions
