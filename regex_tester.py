import re

doc = """# {Plan Title}

## Context

**Problem**: regex named groups failed to compile
**Goal**: capture title, problem, goal, and tests sections

## Dependencies

- Hello
- Hello

## Tasks

- hello

## Files to Modify

| Action | Path | Description |
| ------ | ---- | ----------- |
|        |      |             |
|        |      |             |

## Verification

**Tests**: pytest tests/test_plan_parser.py
**Expected Output**: True
"""
PATTERN = r"^#[ \t]+(?P<title>.+?)[ \t]*\r?\n+##[ \t]+Context[ \t]*\r?\n+\*\*Problem\*\*:[ \t]*(?P<problem>.*?)\r?\n\*\*Goal\*\*:[ \t]*(?P<goal>.*?)\r?\n+##[ \t]+Dependencies[ \t]*\r?\n+(?P<dependencies>(?:[-*][ \t]+.*(?:\r?\n|$))*)\r?\n*##[ \t]+Tasks[ \t]*\r?\n+(?P<tasks>(?:[-*][ \t]+.*(?:\r?\n|$))*)\r?\n*##[ \t]+Files to Modify[ \t]*\r?\n+(?P<files>(?:\|[^|\r\n]*\|[^|\r\n]*\|[^|\r\n]*\|[ \t]*(?:\r?\n|$))+)\r?\n*##[ \t]+Verification[ \t]*\r?\n+\*\*Tests\*\*:[ \t]*(?P<tests>.*?)(?:\r?\n|$)"
matched = bool(re.search(PATTERN, doc, re.MULTILINE))
print(matched)  # True or False
