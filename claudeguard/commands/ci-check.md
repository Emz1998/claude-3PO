---
name: ci-check
description: Phase 11 — Check CI pipeline status and fix failures if needed.
argument-hint: <optional-pr-number>
model: sonnet
---

**Phase 11: CI Check**

Verify that the CI pipeline passes for the pull request created in the `/pr-create` phase.

## Instructions

1. Run `gh pr checks <pr-number> --json name,state,conclusion` to get CI status
2. If all checks pass → advance to next phase
3. If any checks fail:
   - Read the failing check logs
   - Fix the issue in code
   - Push the fix and re-check

## Constraints

- PR must be created before invoking this phase
- CI check commands must include `--json` flag for parseable output
- Only `gh run view`, `gh run list`, `gh run watch`, `gh pr checks`, `gh pr status` commands are allowed
