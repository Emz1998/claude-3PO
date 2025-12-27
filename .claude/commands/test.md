---
name: test
description: Test the codebase
allowed-tools: Bash(python3 :*)
argument-hint: <task-id> <status>
model: sonnet
---

!`python3 .claude/scripts/roadmap_status/roadmap_status.py $ARGUMENTS`
