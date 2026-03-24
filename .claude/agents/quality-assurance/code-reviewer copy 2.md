---
name: Test
description: Code Review config
tools: Read, Grep, Glob, Skill, Write
model: opus
color: red
hooks:
  PreToolUse:
    - matcher: "Write"
      hooks:
        - type: command
          command: "python3 '/home/emhar/avaris-ai/.claude/hooks/workflow/review/report_guard.py'"
  Stop:
    - hooks:
        - type: command
          command: "python3 '/home/emhar/avaris-ai/.claude/hooks/workflow/review/report_ensurer.py'"
---

Dont do anything. Just say "I acknowledge the code review request."
