---
name: code-review
description: Create implementation plan by delegating to strategic-planner and consulting-expert agents
allowed-tools: Read, Write, Glob, Grep, Task
argument-hint: <instructions>
model: sonnet
---

Trigger @code-reviewer agent to review the code

## Dry Run Checklist

**1. Phase Reminder Test**

```
Action: Check if reminder appears in context after phase starts
Expected: Content from config/reminders/code-review.md
Verify: Contains "Purpose:", "Deliverables:", "Key Focus:", "Next Phase:"
Report: [PHASE] code-review - Reminder: LOADED/FALLBACK/MISSING | Structure: VALID/INVALID
```

**2. Deliverables Test**

```
Priority 1 (read):  misc/code-test_*.md
Priority 2 (write): reviews/code-review_*.md

Action: Attempt write before read
Expected: Guardrail blocks write until read completes
Report: [DELIVERABLE] code-review - Read: PASS/FAIL | Write: PASS/FAIL | Order: VALID/INVALID
```

**3. Transition Test**

```
Prior phase: write-code (required)
Next phase: /refactor
Action: Trigger /refactor after code-review completes
Expected: Transition allowed
```
