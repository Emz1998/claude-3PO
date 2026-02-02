---
name: review-test
description: Create implementation plan by delegating to strategic-planner and consulting-expert agents
allowed-tools: Read, Write, Glob, Grep, Task
argument-hint: <instructions>
model: sonnet
---

Trigger @test-reviewer agent to review the tests

## Dry Run Checklist

**1. Phase Reminder Test**

```
Action: Check if reminder appears in context after phase starts
Expected: Content from config/reminders/review-test.md
Verify: Contains "Purpose:", "Deliverables:", "Key Focus:", "Next Phase:"
Report: [PHASE] review-test - Reminder: LOADED/FALLBACK/MISSING | Structure: VALID/INVALID
```

**2. Deliverables Test**

```
Priority 1 (read):  tests/test-summary_*.md
Priority 2 (write): tests/test-quality-report_*.md

Action: Attempt write before read
Expected: Guardrail blocks write until read completes
Report: [DELIVERABLE] review-test - Read: PASS/FAIL | Write: PASS/FAIL | Order: VALID/INVALID
```

**3. Transition Test**

```
Prior phase: write-test (required)
Next phase: /write-code
Action: Trigger /write-code after review-test completes
Expected: Transition allowed
```
