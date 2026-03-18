---
name: test-2
description: Test command
hooks:
  PreToolUse:
    - hooks:
        - type: command
          command: "python3 '.claude/hooks/tests/hook_test.py' --file-path 'tmp/test-2.log'"
          timeout: 10

  Stop:
    - hooks:
        - type: command
          command: "python3 '.claude/hooks/tests/hook_test.py' --file-path 'tmp/test-2.log'"
          timeout: 10
---

Please read `prompt.md` file and answer the question.
