---
name: plan
description: dry run of the plan phase
allowed-tools: Read, Write, Glob, Grep, Task
argument-hint: <instructions>
model: sonnet
---

Trigger @planner agent to create the implementation plan

## Dry Run Checklist

**1. Phase Reminder Test**

```
Action: Check if reminder appears in context after phase starts
Expected: Content from config/reminders/plan.md
Verify: Contains "Purpose:", "Deliverables:", "Key Focus:", "Next Phase:"
Report: [PHASE] plan - Reminder: LOADED/FALLBACK/MISSING | Structure: VALID/INVALID
```

**2. Deliverables Test**

```
Priority 1 (read):  codebase-status/codebase-status_*.md
Priority 2 (write): plans/initial-plan_*.md

Action: Attempt write before read
Expected: Guardrail blocks write until read completes
Report: [DELIVERABLE] plan - Read: PASS/FAIL | Write: PASS/FAIL | Order: VALID/INVALID
```

**3. Transition Test**

```
Prior phase: explore (required)
Next phase: /plan-consult
Action: Trigger /plan-consult after plan completes
Expected: Transition allowed
```
