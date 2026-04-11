---
name: write-report
description: Phase 12 — Write a final implementation report summarizing the work done.
argument-hint: <optional-additional-context>
model: sonnet
---

**Phase 12: Write Report**

Write a final report summarizing the implementation.

## Instructions

1. Write the report to `.claude/reports/latest-report.md`
2. Archive the previous report (if any) to `.claude/reports/archive/`
3. Include in the report:
   - Summary of changes made
   - Files created/modified
   - Test results
   - PR number and branch name
   - Any known limitations or follow-up items

## Report Metadata

Add frontmatter with:
```yaml
---
timestamp: <ISO timestamp>
date: <YYYY-MM-DD>
story_implemented: <story-id>
pr_number: <number>
branch_name: <branch>
sprint_number: <number>
---
```

## Constraints

- This is a docs-write phase — only the report file path is writable
- Must be the last phase before presenting to the user
