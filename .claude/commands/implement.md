---
name: implement
description: Implement tasks, milestones, or phases from roadmap.md using the full workflow
allowed-tools: Read, Bash, SlashCommand, TodoWrite, AskUserQuestion, Skill
argument-hint: TNNN
model: opus
---

**Goal**: Orchestrate implementation of a task through the full build cycle

## Context

- Valid arguments: `TNNN` or `TNNN - TNNN` E.g `T001` or `T001 - T003` (Note for range, respect the white space)
- If no argument is provided, complete 1 user story and its associated tasks (see `project/version/{current-epic-id}/{current-feature-id}/contexts/context_${CLAUDE_SESSION_ID}_{MMDDYY}.md`)
- Hook system activates on `/implement` and enforces phase order and guardrails
- Phases are sequential - cannot skip or go backwards
- Each phase maps to a `workflow:*` skill
- One task at a time - finish or explicitly block before moving on

## Instructions

- The test strategy is determined by the finalized plan. Use the matching sequence below.
- If `TDD` or `TA` is not specified in the plan, use the default test strategy.
- If `Skip planning` is specified in the plan, skip Phase 1 and go directly to Phase 2.

## Workflow

**Phase 0: Context**

1. Read the context from `project/version/{current-epic-id}/{current-feature-id}/contexts/context_${CLAUDE_SESSION_ID}_{MMDDYY}.md`
2. Gather task spec, acceptance criteria, and builder notes

**Phase 1: Planning**

_If `Skip planning` is specified in the plan, skip this phase._

1. Call `workflow:explore` to analyze the codebase
2. Call `workflow:plan` to create the implementation plan
3. Call `workflow:plan-consult` to review the plan
4. Call `workflow:finalize-plan` to finalize the plan

**Phase 2: Implementation**

_The test strategy is determined by the finalized plan._

- **TDD** (tests first):
  1. `workflow:write-failing-tests` - write failing tests (Red)
  2. `workflow:review-tests` - review test quality
  3. `workflow:write-code` - write code to pass the tests (Green)
  4. `workflow:code-review` - review the code
  5. `workflow:refactor` - refactor if needed

- **TA** (test after):
  1. `workflow:code` - write the implementation
  2. `workflow:write-failing-tests` - write tests for the code
  3. `workflow:review-tests` - review test quality
  4. `workflow:code-review` - review the code
  5. `workflow:refactor` - refactor if needed

- **None** (no tests):
  1. `workflow:code` - implement the task

**Phase 3: Quality Gate**

1. Run `npm run check` (types, lint, tests must all pass)
2. If any check fails, fix issues and re-run before proceeding

**Phase 4: QA Review**

1. Run QA review to verify each acceptance criterion is met or not met
2. If QA fails, feed issues back to Builder and re-run (max 3 loops)
3. If max loops exceeded, the task spec needs rewriting - stop and escalate

**Phase 5: Code Review**

1. Call `workflow:code-review` to check standards compliance
2. If review fails, feed issues back to Builder and re-run (max 2 loops)
3. If max loops exceeded, stop and escalate

**Phase 6: Commit**

1. Call `workflow:commit` to commit the changes
2. Update sprint.md task status to Done
3. Call `log:task` to log task completion

## Rules

- **MUST** trigger every `workflow:*` skill sequentially in order
- **MUST** follow the test strategy defined in the finalized plan
- **NEVER** skip any phase - the hook system will block out-of-order transitions
- **MUST** run `npm run check` before QA review
- **MUST** respect loop limits: QA max 3, Code Review max 2
- **MUST** use fresh context for QA and Code Review agents
- **MUST** update sprint.md immediately when task status changes
- **MUST** create a summary report at `project/{version}/{current-epic-id}/{current-feature-id}/summary/summary-report_${CLAUDE_SESSION_ID}_{MMDDYY}.md`

## Acceptance Criteria

- All workflow phases completed in order matching the test strategy
- `npm run check` passes (types, lint, tests)
- QA review passes (all acceptance criteria met)
- Code review passes (standards compliance)
- Hook system validates pass (no phase transition errors)
- sprint.md updated with task status
- Summary report created at the correct path
- Task logged via `log:task`
