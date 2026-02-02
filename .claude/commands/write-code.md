---
name: write-code
description: Write code to pass existing failing tests
allowed-tools: Read, Write, Glob, Grep, Task
argument-hint: <instructions>
model: sonnet
---

Write minimal code to pass the failing tests

## Dry Run Checklist

**1. Phase Reminder Test**

```
Action: Check if reminder appears in context after phase starts
Expected: Content from config/reminders/write-code.md
Verify: Contains "Purpose:", "Deliverables:", "Key Focus:", "Next Phase:", "TDD Green"
Report: [PHASE] write-code - Reminder: LOADED/FALLBACK/MISSING | Structure: VALID/INVALID
```

**2. Deliverables Test**

```
Priority 1 (read):  plans/final-plan_*.md
Priority 2 (write): misc/code-test_*.md

Action: Attempt write before read
Expected: Guardrail blocks write until read completes
Report: [DELIVERABLE] write-code - Read: PASS/FAIL | Write: PASS/FAIL | Order: VALID/INVALID
```

**3. Transition Test**

```
Prior phase: review-test (required)
Next phase: /code-review
Action: Trigger /code-review after write-code completes
Expected: Transition allowed
```
