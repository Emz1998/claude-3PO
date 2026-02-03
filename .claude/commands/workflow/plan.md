---
name: plan
description: Create implementation plan from research and codebase exploration reports by delegating to strategic-planner agent
allowed-tools: Task, Glob, Read
argument-hint: <initial or final>
model: sonnet
agent: planner
---

**Goal**: Invoke the strategic-planner agent to create a comprehensive implementation plan based on validated research reports from the research-specialist
**Plan Phase**: $ARGUMENTS

## Main Instructions

1. If $ARGUMENTS is not empty but it's not `initial` or `final`, please exit and inform the user that the plan phase/arguments is invalid.
2. If $ARGUMENTS is initial, create a prompt for the planner agent based on the initial plan instructions (see `Initial Plan Instructions` section)
3. If $ARGUMENTS is final, create a prompt for the planner agent based on the final plan instructions (see `Final Plan Instructions` section)

## Workflow

1. Create a prompt for the planner agent based on the initial or final plan instructions
2. Trigger the planner agent with the prompt
3. Report the agent's work to the user

## Initial Plan Instructions

<!-- prettier-ignore -->
_Ensure the codebase status report is read first and foremost from `project/{current-version}/{EPIC_ID}/{FEATURE_ID}/codebase-status/codebase-status_${CLAUDE_SESSION_ID}_{MMDDYY}.md`_

**These following sections must be included in the plan**:

- Plan must include a clear objective statement.
- Goals and priorities must be defined
- In-scope and out-of-scope boundaries must be mentioned
- List all subtasks for the tasks to be implemented
- Order the subtasks by priority
- Ensure each subtask is actionable and has a clear owner
- List all files that will be touched
- New files to be created
- Plan must be high level and not too detailed
- Identify risks and provide mitigation strategies
- Include DoD for each subtask

**These sections are optional and context dependent**:

- Include architecture and design decisions if applicable
- Setup for dependencies and library if applicable
- Setup for configuration and environment if applicable
- Include testing requirements if applicable(If TDD or TA is not specified, then no testing requirements are needed)

**IMPORTANT**: Do not overcomplicate solutions. Keep it simple and efficient.

<!-- prettier-ignore -->
_Output the plan to `project/{current-version}/{EPIC_ID}/{FEATURE_ID}/plans/initial-plan_${CLAUDE_SESSION_ID}_{MMDDYY}.md`_

## Final Plan Instructions

<!-- prettier-ignore -->
_Ensure the initial plan and plan consultation report are read first and foremost from `project/{current-version}/{EPIC_ID}/{FEATURE_ID}/plans/initial-plan_${CLAUDE_SESSION_ID}_{MMDDYY}.md` and `project/{current-version}/{EPIC_ID}/{FEATURE_ID}/plans/plan-consultation_${CLAUDE_SESSION_ID}_{MMDDYY}.md`_

- Incorporate feedback from the plan consultation report
- Update the plan to reflect the feedback
- Output the final plan to `project/{current-version}/{EPIC_ID}/{FEATURE_ID}/plans/final-plan_${CLAUDE_SESSION_ID}_{MMDDYY}.md`
