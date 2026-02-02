---
name: finalize-plan
description: Create implementation plan by delegating to strategic-planner and consulting-expert agents
allowed-tools: Read, Write, Glob, Grep, Task
argument-hint: <instructions>
model: sonnet
---

Trigger @planner agent to finalize the implementation plan

## Dry Run Checklist

**1. Phase Reminder Test**

```
Action: Check if reminder appears in context after phase starts
Expected: Content from config/reminders/finalize-plan.md
Verify: Contains "Purpose:", "Deliverables:", "Key Focus:", "Next Phase:"
Report: [PHASE] finalize-plan - Reminder: LOADED/FALLBACK/MISSING | Structure: VALID/INVALID
```

**2. Deliverables Test**

```
Priority 1 (read):  plans/plan-consultation_*.md
Priority 2 (write): plans/final-plan_*.md

Action: Attempt write before read
Expected: Guardrail blocks write until read completes
Report: [DELIVERABLE] finalize-plan - Read: PASS/FAIL | Write: PASS/FAIL | Order: VALID/INVALID
```

**3. Transition Test**

```
Prior phase: plan-consult (required)
Next phase: /write-test
Action: Trigger /write-test after finalize-plan completes
Expected: Transition allowed
```
