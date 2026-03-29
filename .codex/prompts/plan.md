---
name: plan
description: Create implementation plan from user instructions by delegating to planner agent
allowed-tools: Task, Read, Glob, Grep, AskUserQuestion, TodoWrite, Agent, Write, WebFetch, WebSearch, ExitPlanMode
argument-hint: [--skip-explore] [--skip-research] [--skip-all] <planning-instructions>
model: opus
---

**Goal**: Create an actionable implementation plan by running exploration, planning, and review agents in sequence — enforced by the plan guardrail.

## Arguments

- `$ARGUMENTS` — optional skip flags followed by free-form planning instructions
  - `--skip-explore` — skip the 3 Explore agents
  - `--skip-research` — skip the 2 Research agents
  - `--skip-all` — skip all explore/research agents, go straight to planning
  - Anything after the flags is treated as planning instructions (e.g. `/plan --skip-explore Add dark mode support`)
- If no instructions provided, ask the user what they want to plan before proceeding

## Workflow

The guardrail enforces this phase sequence automatically. Follow it strictly.

### Phase 1: Explore (skippable)

Launch in parallel (foreground):

- **3 × `Explore` agents** — each focused on a different area of the codebase
- **2 × `Research` agents** — researching patterns, docs, and prior art relevant to the task

Skip with `--skip-explore`, `--skip-research`, or `--skip-all`.

> The guardrail automatically advances to Phase 2 once all required agents complete.

### Phase 2: Plan

- Invoke the **`Plan` built-in agent** with the exploration findings and user instructions
- The Plan agent produces a structured implementation plan following the plan template
- Plan must include: `## Context`, `## Approach` or `## Steps`, `## Files to Modify` or `## Critical Files`, `## Verification`

### Phase 3: Review

- Invoke the **`Plan-Review` agent** to review the plan
- Scores are parsed automatically (confidence + quality, threshold: 80/80)
- If scores are below threshold: revise and re-review (max 3 iterations)
- If max iterations reached without passing: phase transitions to `failed`

### Phase 4: Write

- Write the finalized plan to **`.claude/plans/<plan-name>.md`**
- The guardrail blocks writes outside `.claude/plans/`

### Phase 5: Exit

- Call `ExitPlanMode`
- The guardrail validates the plan file against the template
- If required sections are missing: blocked with a list of what's missing
- If valid: plan content is surfaced as additional context

## Rules

- **MUST** follow the phase sequence — the guardrail enforces it and will block out-of-order agents
- **MUST** save the plan to `.claude/plans/` — writes elsewhere are blocked
- **MUST** call `ExitPlanMode` after writing — required for template validation
- **DO NOT** use agent types other than `Explore`, `Research`, `Plan`, `Plan-Review`
- **DO NOT** proceed to write until the Plan-Review agent approves (scores >= 80/80)

## Acceptance Criteria

- All required explore/research agents completed (or skipped via flags)
- Plan created by `Plan` agent and approved by `Plan-Review` agent
- Plan saved to `.claude/plans/` with all required template sections
- `ExitPlanMode` called and template validation passed
