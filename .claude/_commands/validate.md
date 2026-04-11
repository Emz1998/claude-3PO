---
name: validate
description: Validate the current changes before pushing
hooks:
  PreToolUse:
    - hooks:
        - type: command
          command: "python3 '$CLAUDE_PROJECT_DIR/.claude/hooks/workflow/guards/phase_guard.py' create-pr validate"
          timeout: 10
---

Run validation checks on the current changes before pushing.
