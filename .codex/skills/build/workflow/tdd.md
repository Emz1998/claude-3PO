# TDD Workflow

**Goal**: Create failing tests if `TDD` is specified in test strategy.

## Instructions

- If the confidence score provided by the `code-reviewer` subagent is less than 80%, make the necessary changes. Then, re-invoke `agent-code-reviewer` to review the code again and repeat the process until the confidence score is 80% or higher.

## Workflow

1. Invoke `agent-test-engineer` subagent to create failing tests if `TDD` is specified in test strategy.
2. Invoke @agent-version-manager to commit the changes
3. Invoke the task owners subagents to implement their own task
4. Invoke @agent-code-reviewer to perform a peer review of the code
5. Read the code review report, iterate and make necessary changes till the confidence score is 80% or higher
6. Once the code is reviewed and approved, invoke @agent-version-manager again to commit the changes
