---
name: plan
description: Create implementation plan from user instructions by delegating to planner agent
allowed-tools: Task, Read, Glob, Grep, AskUserQuestion, TodoWrite
argument-hint: <planning-instructions>
model: opus
---

**Goal**: Create an actionable implementation plan by delegating to the `planning-specialist` subagent based on user instructions

## Context

- Arguments: `$ARGUMENTS` (user's planning instructions, feature description, or task scope)
- If no arguments provided, ask the user what they want to plan

## Workflow

### Phase 1: Gather Context

1. If `$ARGUMENTS` is empty, use `AskUserQuestion` to ask the user what they want to plan
2. Invoke `agent-codebase-explorer` subagent to analyze relevant parts of the codebase and produce a codebase report
3. Read the codebase report output

### Phase 2: Create Plan

1. Invoke `agent-planning-specialist` subagent with the codebase report and user instructions
2. The planner reads the codebase report and generates a structured implementation plan
3. Present the plan to the user for review using `AskUserQuestion`

### Phase 3: Finalize

1. If user requests changes, re-invoke `agent-planning-specialist` with the feedback
2. Once approved, save the finalized plan to the appropriate project directory
3. Report plan location and summary to the user

## Rules

- **NEVER** create a plan without first gathering codebase context via `agent-codebase-explorer`
- **NEVER** finalize a plan without user approval
- **DO NOT** include implementation details beyond what the planner agent produces
- **DO NOT** skip the codebase exploration phase
- **MUST** pass user instructions verbatim to the planner agent

## Acceptance Criteria

- Codebase report generated before planning begins
- Implementation plan created with phases, tasks, and file modifications
- User reviewed and approved the plan
- Finalized plan saved to the project directory