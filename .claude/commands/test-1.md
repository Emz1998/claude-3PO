---
name: test-1
description: Test command
hooks:
  PreToolUse:
    - hooks:
        - type: command
          command: "python3 '.claude/hooks/tests/hook_test.py' --file-path 'tmp/test-1.log'"
          timeout: 10

  Stop:
    - hooks:
        - type: command
          command: "python3 '.claude/hooks/tests/hook_test.py' --file-path 'tmp/test-1.log'"
          timeout: 10
---

Dont do anything. Just say Hi! I'm from test-1.
