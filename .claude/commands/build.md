---
name: build
description: Implement tasks, milestones, or phases from roadmap.md using the full workflow
allowed-tools: Read, Bash, SlashCommand, TodoWrite, AskUserQuestion, Skill
argument-hint: continue
model: opus
---

**Goal**: Implement specified task(s), milestone(s), or phase(s) using the full workflow

## Context

- Workflow (Skills): `roadmap:query` → `/explore` → `/discuss` → `/plan` → `/prototype` → `/code` -> `/log:task`

## Instructions

- If error occurs, call the `flag:error` Skill to flag the error.
- If blocked, call the `flag:blocked` Skill to flag the blocked task.
- If critical issue occurs, call the `flag:critical` Skill to flag the critical issue.
- If after three flags for each type(error, blocked, critical), `flag:take-over` Skill to take over the task.
- If all options are exhausted, call the `flag:help` Skill to get help from the user.

## Workflow

1. Analyze the roadmap's current phase, milestones, and tasks given by the hook.
2. Trigger every skill in the **Workflow** using the `Skill` tool in sequence.
3. Create a summary report at `project/{version}/{phase}/{milestone}/reports/summary-report_[YYYY-MM-DD].md`

## Constraints

- **MUST** trigger every skill sequentially in the **Workflow**
- **MUST** create a summary report at `project/{version}/{phase}/{milestone}/reports/summary-report_[YYYY-MM-DD].md`
- **MUST** act as an orchestrator and not an implementer.
- **MUST** not skip any steps in the **Workflow**.
