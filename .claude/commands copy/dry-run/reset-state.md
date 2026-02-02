---
name: reset-state
description: Reset workflow state to default
allowed-tools: Bash(python3 :*)
argument-hint: <none>
model: sonnet
---

!`python3 .claude/hooks/workflow/manually-deactivate_workflow.py`
