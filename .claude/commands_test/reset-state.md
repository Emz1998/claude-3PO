---
name: reset-state
description: Reset workflow state to default
allowed-tools: Bash(python3 :*)
argument-hint: <none>
model: sonnet
---

!`python3 .claude/hooks/workflow/manual_state_reset.py`
