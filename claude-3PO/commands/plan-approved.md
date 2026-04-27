---
name: plan-approved
description: Approve the plan and proceed to the next phase
allowed-tools: Bash, Read, Glob, Grep, Write, Edit, Agent
---

The user has reviewed the plan and approves it. Proceed to the next phase.

## What happens

- If plan-review passed (checkpoint), the workflow resumes — next auto-phase starts.
- If plan-review was exhausted (3 failed reviews), the plan is accepted as-is and the workflow proceeds.
- Only the user can invoke this command.
