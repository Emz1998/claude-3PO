---
name: implement
description: Implement the task
allowed-tools: Bash, Read, Glob, Grep, Write
argument-hint: <task-to-implement>
model: opus
---

!`python3 .claude/hooks/workflow/utils/workflow_initializer.py --session-id ${CLAUDE_SESSION_ID} --story-id $0`

Analyze the coding task "$1" and deploy the appropriate engineer agents in parallel for maximum efficiency. Determine which engineers are needed, distribute work intelligently, and aggregate results.

## Story Context

!`python3 github_project/project_manager.py view $0`

## Instructions

- Always plan first before implementing.
- Ensure creation of tests if TDD is specified.
- Only read and write the files that are stated in the plan.
- Ask questions if not sure about the task. Use `AskUserQuestion` to ask questions.
- Must follow the plan template structure strictly

## Workflow

### Task Creation Phase

- Invoke the `Task-Creator` agent to create the task.
- The task creator must ensure that the tasks are identical to the tasks specified in the `Story Context` section.

### Plan Phase

> **IMPORTANT**: You have to ensure that the amount agents triggered is correct or else the hook guardrail will block the `Plan` agent from executing.

1. Trigger the following agents in parallel to explore the codebase and research about the task:

- 3 x `Explore` agents, each focused on critical and relevant areas of the codebase
- 2 x `Research` agents, one focusing on researching the web for solutions to the task and the other for retrieving latest documentation and best practices.

| Agent              | Description                                                                                                |
| ------------------ | ---------------------------------------------------------------------------------------------------------- |
| `Explore` agent 1  | Must analyze the project structure and configuration and identify the critical files and directories       |
| `Explore` agent 2  | Must analyze the git activity and project dependencies and identify the critical files and directories     |
| `Explore` agent 3  | Must analyze the implementation state and technical health and identify the critical files and directories |
| `Research` agent 1 | Must research the web for solutions to the task                                                            |
| `Research` agent 2 | Must retrieve latest documentation and best practices                                                      |

2. Once the exploration and research are complete, invoke the `Plan` agent to formulate the implementation plan.

3. Once the `Plan` task is complete, write the plan to the `.claude/plans/<plan-name>.md` file from current directory.

4. Invoke the `Plan-Review` agent to review the plan.

5. Validate the reviewer's confidence and quality scores. If the scores are not above 80, revise the plan and iterate until the scores are above 80.

6. Then present the plan to the user using `ExitPlanMode` tool.

### Code Phase

1. Once the user approves the plan, validate if TDD is specified, if yes, you have to write failing tests first.
2. Once the failing tests are written, invoke the `Test-Review` agent to review the tests quality.
3. Once the tests are reviewed, write the minimal code to pass the tests.
4. Rerun tests to verify they pass.
5. If the tests are not passing, revise the code and iterate until the tests pass.
6. Invoke the `QA` agent to validate the implementation against the acceptance criteria.
7. If the validation returns `Fail`, revise the code implementation and iterate until the validation passes.
8. Once validation passes, push to the branch and create a pull request.
9. Check if ci pipeline is passing, if not, revise the code and iterate until the ci pipeline passes.
10. Write a final report of the implementation in the `.claude/reports/latest-report.md` file. Copy and archive the previous report to the `.claude/reports/archive/` directory. Add metadata to the latest report in the frontmatter with `timestamp`, `date` , `story_implemented: <story-id>`, `pr_number`, `branch_name`, `sprint_number`.
11. Present the report to the user before stopping.

## Rules

- Always follow the workflow strictly.
- Always validate your work either through tests, sample ui, running a bash command, etc. Never skip any review.
- Always ask questions if not sure about the task. Use `AskUserQuestion` to ask questions.
- Always follow the plan template strictly.

## References

> **Note**: All directories are relative to the current working directory.

- **Plan Directory**: `.claude/plans/`
- **Latest Report Directory**: `.claude/reports/latest-report.md`
- **Past Reports Directory**: `.claude/reports/archive/`
