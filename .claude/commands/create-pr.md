---
name: create-pr
description: Create a pull request for the current changes
hooks:
  PreToolUse:
    - hooks:
        - type: command
          command: "python3 '$CLAUDE_PROJECT_DIR/.claude/hooks/workflow/guards/phase_guard.py' review create-pr"
          timeout: 10
---

Create a pull request for the current branch changes.
