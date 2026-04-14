---
name: continue
description: Force-complete the current phase and proceed
allowed-tools: Bash, Read, Glob, Grep, Write, Edit, Agent
---

Force-complete the current phase and advance the workflow. Use when a phase is stuck or the user wants to skip it.

> **Note:** For plan-review, use `/plan-approved` to approve the plan, or `/revise-plan` to revise it. `/continue` does not handle plan-review.

## What happens

- If the current phase is already completed, the next auto-phase starts.
- If the current phase is in progress, it is force-completed and the next auto-phase starts.
- The next phase starts automatically (if it's an auto-phase) or waits for you to invoke the next skill.

## Next steps

After `/continue` succeeds, check which phase is current and proceed accordingly. Invoke the next skill in the workflow sequence.
