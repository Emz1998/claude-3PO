---
name: refactor
description: Refactor and clean up code while keeping tests in src/tests/ passing
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task, TodoWrite
model: sonnet
hooks:
  Stop:
    - hooks:
        - type: command
          command: "python3 '/home/emhar/avaris-ai/.claude/hooks/workflow/review/refactor.py'"
---

Dont do anything, just say "I acknowledge the refactoring request."
