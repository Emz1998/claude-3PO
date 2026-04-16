---
name: revise-plan
description: Revise the plan after checkpoint or exhaustion
allowed-tools: Read, Edit, Glob, Grep, Agent
argument-hint: <revision-instructions>
---

The plan-review has reached a checkpoint (passed) or exhaustion (3 failed reviews). The user wants revisions before proceeding.

## Instructions

1. Read the current plan at `.claude/plans/latest-plan.md`.
2. Apply the requested changes: "$1"
3. Edit the plan file with the revisions. The guardrail requires at least one edit before re-invoking PlanReview.
4. After editing, invoke the **PlanReview** agent to re-score the revised plan.
5. If scores pass, the workflow will discontinue again at checkpoint for final approval.

## Rules

- You MUST edit the plan file before invoking PlanReview — the guardrail blocks re-review without edits.
- Do not remove required sections (Dependencies, Tasks, Files to Modify for build; Context, Approach, Files to Create/Modify, Verification for implement).
- The plan template format must be preserved.
- Review count resets on revise, giving a fresh cycle of up to 3 reviews.
