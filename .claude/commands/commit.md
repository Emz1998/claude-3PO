---
name: commit
description: Commit the changes to the remote repository
hooks:
  PreToolUse:
    - hooks:
        - type: command
          command: "python3 '$CLAUDE_PROJECT_DIR/.claude/hooks/workflow/guards/phase_guard.py' review final-commit"
          timeout: 10
---

Successfully Committed Changes
