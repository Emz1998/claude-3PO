---
name: commit
description: Commit the changes to the remote repository
allowed-tools: Bash(git add:*), Bash(git commit:*)
model: sonnet
---

Trigger @version-manager agent to commit the changes

## Dry Run Checklist

**1. Phase Reminder Test**

```
Action: Check if reminder appears in context after phase starts
Expected: Content from config/reminders/commit.md
Verify: Contains "Purpose:", "Deliverables:", "Key Focus:", "Workflow Complete"
Note: Should NOT contain "Next Phase:" (final phase)
Report: [PHASE] commit - Reminder: LOADED/FALLBACK/MISSING | Structure: VALID/INVALID
```

**2. Deliverables Test**

```
Priority 1 (read):  reports/validation_report_*.md
Priority 2 (write): reports/commit_*.md

Action: Attempt write before read
Expected: Guardrail blocks write until read completes
Report: [DELIVERABLE] commit - Read: PASS/FAIL | Write: PASS/FAIL | Order: VALID/INVALID
```

**3. Transition Test**

```
Prior phase: validate (required)
Next phase: None (final phase)
Action: Workflow complete - generate summary report
Expected: All 11 phases passed
```

## Final Summary Report

```
PHASE REMINDERS:  11/11 LOADED | 11/11 VALID
DELIVERABLES:     11/11 READ PASS | 11/11 WRITE PASS | 11/11 ORDER VALID
TRANSITIONS:      10/10 ALLOWED (explore→plan→...→commit)
```
