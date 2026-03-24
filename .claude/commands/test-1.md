---
name: test-1
description: Test command
hooks:
  Stop:
    - hooks:
        - type: command
          command: "python3 '.claude/hooks/tests/hook_schema_test/general_test.py'"
          timeout: 30
---

Hello Claude! what do you think is the future of AI?
