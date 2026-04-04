# Troubleshoot Workflow

**Goal**: Troubleshoot errors, bugs, or issues encountered during the implementation of the current task.

## Workflow

1. Invoke `agent-troubleshooter` subagent to troubleshoot the errors, bugs, or issues encountered during the implementation of the current task.
2. Read the troubleshooting report and make necessary changes.
3. Invoke @fullstack-developer to fix the errors, bugs, or issues encountered during the implementation of the current task.
4. Retest the code to ensure the errors, bugs, or issues are resolved.
5. If errors, bugs, or issues persist, invoke `agent-gpt-manager` and `agent-gemini-manager` to get second opinions from GPT and Gemini models.
6. Read the troubleshooting report from GPT and Gemini and make necessary changes.
7. Retest the code to ensure the errors, bugs, or issues are resolved.
8. If errors, bugs, or issues persist, invoke `/help` `SlashCommand/Skill` tool to get help from the user.
