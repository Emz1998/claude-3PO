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

`dry-run:explore` → `dry-run:plan` → `dry-run:plan-consult` → `dry-run:finalize-plan` → `dry-run:write-test` → `dry-run:review-test` → `dry-run:write-code` → `dry-run:code-review` → `dry-run:refactor` → `dry-run:validate` → `dry-run:commit`

## Prohibited Actions

- Do not make code changes
- Do not create commits
- Do not manually edit cache to fake transitions
