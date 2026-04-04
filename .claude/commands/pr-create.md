---
name: pr-create
description: Phase 8 — Invoke the version-manager agent to create a pull request with conventional commits.
argument-hint: <optional-additional-context>
model: sonnet
---

**Phase 8: Create Pull Request**

Invoke 1 `version-manager` agent to commit all changes and open a pull request.

## Instructions

1. Launch 1 `version-manager` agent with:
   - The story/task description and summary of changes made
   - Instruction to stage and commit all changes using conventional commit format
   - Instruction to push the branch and create a PR against the main branch
   - PR title and body should summarize: what changed, why, and how to test it

## Conventional Commit Format

```
<type>(<scope>): <short description>

[optional body]
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

## Completion

Once the `version-manager` agent completes, return the PR URL to the user.
