---
name: write-test
description: Create implementation plan by delegating to strategic-planner and consulting-expert agents
allowed-tools: Read, Write, Glob, Grep, Task
argument-hint: <instructions>
model: sonnet
---

Trigger @test-engineer agent to write the tests

## Dry Run Checklist

**1. Phase Reminder Test**

```
Action: Check if reminder appears in context after phase starts
Expected: Content from config/reminders/write-test.md
Verify: Contains "Purpose:", "Deliverables:", "Key Focus:", "Next Phase:", "TDD Red"
Report: [PHASE] write-test - Reminder: LOADED/FALLBACK/MISSING | Structure: VALID/INVALID
```

**2. Deliverables Test**

```
Priority 1 (read):  plans/final-plan_*.md
Priority 2 (write): tests/test-summary_*.md

Action: Attempt write before read
Expected: Guardrail blocks write until read completes
Report: [DELIVERABLE] write-test - Read: PASS/FAIL | Write: PASS/FAIL | Order: VALID/INVALID
```

**3. Transition Test**

```
Prior phase: finalize-plan (required)
Next phase: /review-test
Action: Trigger /review-test after write-test completes
Expected: Transition allowed
```
