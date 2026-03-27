---
name: build
description: Implement the current task in the roadmap by delegating to the appropriate subagent
---

**Goal**: Implement the current task in the roadmap by delegating to the appropriate subagent

## Instructions

- The main agent is only responsible for orchestration the subagents to implement the current task and shouldn't perform any coding tasks.
- If `TDD` is specified in test strategy, read the `.claude/skills/build/workflow/tdd.md` file and follow the workflow
- If `TA` or `Test-After` is specified in test strategy, read the `.claude/skills/build/workflow/test-after.md` file and follow the workflow

## Workflow

1. Read the `todo` tasks from `project/{current_version}/{current_phase}/{current_milestone}/todos/todo_{current_date(YYYY-MM-DD)}_{current_session_id}` file.
1. Invoke @agent-explorer to explore the codebase to understand project structure, relevant files, and current state.
1. Invoke @agent-planner to create an implementation plan for the current task.
1. Invoke @agent-consultant to review and consult on the plan.
1. Read the appropriate coding workflow in `.claude/skills/build/workflow/[workflow].md` file and follow the workflow
1. Provide a summary report to the user containing the tasks completed, acceptance criteria met, and any issues encountered.

**Special Cases**

- If errors, bugs, or issues are encountered, read the `.claude/skills/build/workflow/troubleshoot.md` file and follow the workflow

## Constraints

- DO NOT perform any coding tasks yourself. Only delegate to the appropriate subagents.
