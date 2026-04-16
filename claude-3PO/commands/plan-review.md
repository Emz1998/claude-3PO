---
name: plan-review
description: Phase 4 — Invoke the PlanReview agent to score the implementation plan.
argument-hint: <optional-additional-context>
model: sonnet
---

**Phase 4: Plan Review**

Invoke 1 `PlanReview` agent to evaluate the implementation plan.

## Instructions

1. Launch 1 `PlanReview` agent with:
   - The plan file written in the `/plan` phase
   - Instruction to evaluate: completeness, feasibility, clarity, and risk
   - Must output confidence and quality scores

## Score Format

The `PlanReview` agent must output scores in this format:
```
Confidence Score: [0-100]
Quality Score: [0-100]
```

## Evaluation

The guardrail hook parses the reviewer's output:
- **Both scores >= 80** → plan approved, advance to next phase
- **Any score < 80** → revision needed (sub-phase: `plan-revision`)
- Maximum 3 review iterations

## Constraints

- Plan must be written to `.claude/plans/` before invoking this phase
- Do not modify the plan during review — revisions happen in the `plan-revision` sub-phase
