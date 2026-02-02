---
name: refactor
description: Create implementation plan by delegating to strategic-planner and consulting-expert agents
allowed-tools: Read, Write, Glob, Grep, Task
argument-hint: <instructions>
model: sonnet
---

Refactor and clean up code while keeping tests passing

## Dry Run Checklist

**1. Phase Reminder Test**

```
Action: Check if reminder appears in context after phase starts
Expected: Content from config/reminders/refactor.md
Verify: Contains "Purpose:", "Deliverables:", "Key Focus:", "Next Phase:", "TDD Refactor"
Report: [PHASE] refactor - Reminder: LOADED/FALLBACK/MISSING | Structure: VALID/INVALID
```

**2. Deliverables Test**

```
Priority 1 (read):  reviews/code-review_*.md
Priority 2 (write): reports/refactor_*.md

Action: Attempt write before read
Expected: Guardrail blocks write until read completes
Report: [DELIVERABLE] refactor - Read: PASS/FAIL | Write: PASS/FAIL | Order: VALID/INVALID
```

**3. Transition Test**

```
Prior phase: code-review (required)
Next phase: /validate
Action: Trigger /validate after refactor completes
Expected: Transition allowed
```
