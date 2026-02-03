---
name: implement
description: Implement tasks, milestones, or phases from roadmap.md using the full workflow
allowed-tools: Read, Bash, SlashCommand, TodoWrite, AskUserQuestion, Skill
argument-hint: MS-NNN
model: opus
---

**Goal**: Orchestrate implementation of a milestone through the full workflow

## Context

- Valid arguments: `TNNN` or `TNNN - TNNN` E.g `T001` or `T001 - T003` (Note for range, respect the white space)

- If no argument is provided, complete 1 user story and its associated tasks. (See `project/version/{current-epic-id}/{current-feature-id}/contexts/context_${CLAUDE_SESSION_ID}_{MMDDYY}.md` for tasks)

- Hook system activates on `/implement ` and enforces phase order and guardrails
- Phases are sequential - cannot skip or go backwards
- Each phase maps to a `workflow:*` skill
- Test strategy (TDD, TA, or none) determines which implementation skills are called

## Instructions

- The test strategy is determined by the finalized plan. Use the matching sequence below.

- If `TDD` or `TA` is not specified in the plan, use the default test strategy.

- If `Skip implementation` is specified in the plan, skip the planning phase and go directly to the implementation phase.

## Workflow

**Phase 0: Context**

1. Read the context of the current task from `project/version/{current-epic-id}/{current-feature-id}/contexts/context_${CLAUDE_SESSION_ID}_{MMDDYY}.md`

**Phase 1: Planning**

<!-- prettier-ignore -->
_If `Skip planning` is specified in the plan, skip this phase._

1. Call `workflow:explore` to analyze the codebase
2. Call `workflow:plan` to create the implementation plan
3. Call `workflow:plan-consult` to review the plan
4. Call `workflow:finalize-plan` to finalize the plan

**Phase 2: Implementation**

_The test strategy is determined by the finalized plan. Use the matching sequence below._

- **TDD** (tests first):
  1. `workflow:tdd-write-failing-tests` - write failing tests
  2. `workflow:review-tests` - review test quality
  3. `workflow:tdd-write-code` - write code to pass the tests
  4. `workflow:code-review` - review the code
  5. `workflow:refactor` - refactor if needed

- **TA** (test after):
  1. `workflow:ta-write-code` - write the implementation
  2. `workflow:ta-write-failing-tests` - write tests for the code
  3. `workflow:review-tests` - review test quality
  4. `workflow:code-review` - review the code
  5. `workflow:refactor` - refactor if needed

- **None** (no tests):
  1. `workflow:implement` - directly implement the task

6. Call `log:task` to log task completion

**Phase 3: Validation**

1. Call `workflow:validate` to validate the implementation

**Phase 3: Commit**

1. Call `workflow:commit` to commit the changes

## Rules

- **MUST** trigger every `workflow:*` skill sequentially in order
- **MUST** follow the test strategy defined in the finalized plan
- **NEVER** skip any phase - the hook system will block out-of-order transitions
- **MUST** create a summary report at `project/{version}/{current-epic-id}/{current-feature-id}/summary/summary-report_${CLAUDE_SESSION_ID}_{MMDDYY}.md`

## Acceptance Criteria

- All workflow phases completed in order matching the test strategy
- Hook system validates pass (no phase transition errors)
- Summary report created at the correct path
- Task logged via `log:task`
