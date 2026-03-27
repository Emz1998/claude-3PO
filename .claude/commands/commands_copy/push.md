---
name: push
description: Push the changes to the remote repository
allowed-tools: Bash(git push:*)
model: sonnet
hooks:
  PreToolUse:
    - hooks:
        - type: command
          command: "python3 '$CLAUDE_PROJECT_DIR/.claude/hooks/workflow/guards/phase_guard.py' validate push"
          timeout: 10
---

!`git push`

Do not execute the command yourself, just tell me the output.
