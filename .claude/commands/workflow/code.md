---
name: code
description: Implement the current task in the roadmap by delegating to the appropriate subagent
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task, TodoWrite
argument-hint: <task-id>
model: sonnet
---

**Goal**: Implement the current task in the roadmap by delegating to the appropriate subagent

## Instructions

- If the confidence score provided by the `code-reviewer` subagent is less than 80%, make the necessary changes. Then, re-invoke `agent-code-reviewer` to review the code again and repeat the process until the confidence score is 80% or higher.

- Retrieve the test strategy from the hook context.

- If there are errors, bugs, or issues, invoke `agent-troubleshooter` to fix the issues.

- The main agent is only responsible for orchestration the subagents to implement the current task and shouldn't perform any coding tasks.

## Workflow

1. Invoke `agent-test-engineer` subagent to create failing tests if `TDD` is specified in test strategy.
2. Invoke @agent-version-manager to commit the changes
3. Invoke the task owners subagents to implement their own task
4. Invoke @agent-code-reviewer to perform a peer review of the code
5. Read the code review report, iterate and make necessary changes till the confidence score is 80% or higher
6. Once the code is reviewed and approved, invoke @agent-version-manager to commit the changes
