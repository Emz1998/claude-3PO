---
name: test-agent
description: For testing purposes. You do not perform any task or work
tools: Read, Grep, Glob, Skill, Write
model: opus
color: red
hooks:
  Stop:
    - hooks:
        - type: command
          command: "python3 '.claude/hooks/tests/hook_test.py' --file-path 'tmp/stop.log'"
---

Hello Claude!
