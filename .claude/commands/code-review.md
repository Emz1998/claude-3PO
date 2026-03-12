---
name: code-review
description: Custom command
hooks:
  PreToolUse:
    - hooks:
        - type: command
          command: "python3 '$CLAUDE_PROJECT_DIR/.claude/hooks/workflow/guards/phase_guard.py' code review"
          timeout: 10
---

Invoke the `code-reviewer` subagent to review the code changes.
