Don't forget to log the task completion.

Use `log` Skill for logging

If the task is blocked, use `blocked` status.

Skill: `log`
Args: <task_id> <commit_message>

Valid task ID format: `T-NNN`
Valid status: `blocked`, `completed`

Examples:

`log T-001 completed`
`log T-002 blocked`
