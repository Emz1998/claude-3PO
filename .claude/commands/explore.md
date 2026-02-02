---
name: explore
description: Dry run of the explore phase
allowed-tools: Read, Glob, Grep, Task
argument-hint: <context>
model: sonnet
---

Trigger @codebase-explorer agent to explore the codebase

## Dry Run Checklist

**1. Phase Reminder Test**

```
Action: Check if reminder appears in context after phase starts
Expected: Content from config/reminders/explore.md
Verify: Contains "Purpose:", "Deliverables:", "Key Focus:", "Next Phase:"
Report: [PHASE] explore - Reminder: LOADED/FALLBACK/MISSING | Structure: VALID/INVALID
```

**2. Deliverables Test**

```
Priority 1 (read):  prompt.md
Priority 2 (write): codebase-status/codebase-status_*.md

Action: Attempt write before read
Expected: Guardrail blocks write until read completes
Report: [DELIVERABLE] explore - Read: PASS/FAIL | Write: PASS/FAIL | Order: VALID/INVALID
```

**3. Transition Test**

```
Prior phase: None (first phase)
Next phase: /plan
Action: Trigger /plan after explore completes
Expected: Transition allowed
```
