---
name: script
description: Use PROACTIVELY when you need to create, update, configure, or validate Claude Code scripts
argument-hint: <task-to-be-performed> <instructions>
---

**Goal**: Create, update or troubleshoot scripts

**IMPORTANT**: Infer the task to be performed based on the user's request. If not clear, ask the user for more details.

## Instructions

### If the task is to create a new script

- Invoke `EnterPlanMode` tool to enter plan mode.
- Do an exploration of the relevant files and directories in the codebase with Explore agent
- Create a plan with Plan agent
- Once the user approved, implement the plan
- Run `/simplify` skill to clean up the code
- Review the code, fix any issues if any and provide report to main agent

### If the task is to refactor hooks

- Analyze the user revision request. If revision request is vague, ask the user for more details.
- Invoke `EnterPlanMode` tool to enter plan mode.
- Identify all the files that are needed to be revised. If not provided, ask the user for the file path.
- Do an exploration of the relevant files and directories in the codebase with Explore agent
- Create a plan with Plan agent
- Once the user approved, implement the plan
- Run `/simplify` skill to clean up the code
- Review the code, fix any issues if any and provide report to main agent

### If the task is to troubleshoot hooks

- Identify the file that is causing the issue based on the user inputs/arguments. If not provided, ask the user for the file path.
- Run any tests if exists to reproduce the issue
- Review the code to see if there are any issues.
- If issues are found, provide a plan to fix the issue to the user.
- Once approved, implement the fix
- Re run the tests to ensure the issue is fixed
- If any issues persist, reiterate
- If after three tries, the issues are not resolved, escalate to the user
- Provide report to main agent of the issue, blockers and the resolution

## Workflow

1. Determine the task to be performed: create, refactor, or troubleshoot scripts
2. Implement the task based on the instructions above
3. Validate the script against the acceptance criteria
4. Provide report to main agent

## Constraints

- Do not deviate from the plan
- Never skip validation
- Explore, Plan and Execute are a must when creating or refactoring scripts
- Prefer python over shell scripts

## Acceptance Criteria

- Code is written in python
- Solutions are appropriate for the complexity of the task
- Code is robus and resilient to errors
- Script executes successfully
- No errors on test
- Script handles invalid/malformed input gracefully
- Script implementation is simple and not complex
- No security vulnerabilities
