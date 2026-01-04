**Main Goal**: Create a guardrail for the following subagents:

- Frontend Developer
- Backend Developer
- Version Manager
- Test Engineer

**Important:** This guardrail should only run if the `/implement` workflow is triggered via `User Prompt Submit` or `Skill` call.

## Subagent Conditions

- Every subagent must check if the `/implement` workflow is triggered via `user prompt submit` or `skill` call. If not, subagents must not perform the workflow.

_The subagents should only be triggered if these conditions are met for each subagent:_

**Main Agent Conditions:**

- Ensure the subagents are triggered in the correct order and with the correct conditions.

- Must orchestrate the workflow: Read Todo file -> Trigger Codebase Explorer -> Trigger Planner -> Trigger Consultant Check if tdd is specified in the milestone -> Orchestrate coding workflow (see `Coding workflow` section below)

- Read the todo file first in `project/{version}/{phase}/{milestone}/todos/todos_{date}_{session_id}.md`

**Codebase Explorer Conditions:**

- Main agent must have read the todo file first in `project/{version}/{phase}/{milestone}/todos/todos_{date}_{session_id}.md`

**Planner Conditions:**

- Must ensure the codebase explorer has been triggered via post-tool use hook event.

**Consultant Conditions:**

- Must ensure the planner has been triggered via post-tool use hook event.

After this stage, follow the coding workflow below.

## Coding workflow

If TDD is specified in the milestone, trigger the following subagents in this order:

1. Trigger Test Engineer to create failing tests
2. Trigger the appropriate subagent engineer that own the task to write code to pass the tests
3. Trigger Version Manager to commit the tests
4. Trigger Code Reviewer to review the code
5. Trigger Version Manager to commit the changes

If TA is specified, do the following:

1. Trigger the appropriate subagent engineer that own the task to implement the task
2. Trigger test engineer to create tests for the task
3. Trigger Code Reviewer to review the code
4. Trigger Version Manager to commit the changes

If no TDD or TA is specified, do the following:

1. Trigger the appropriate subagent that owns the task to implement the task
2. If it's a coding task, trigger the code-reviewer. If it's a non-coding task, choose and trigger the appropriate subagent in `.claude/agents/quality-assurance/` directory
3. Trigger Version Manager to commit the changes
