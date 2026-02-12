---
name: troubleshoot
description: Enter troubleshoot mode to diagnose and resolve issues (bypasses coding phases)
allowed-tools: Read, Glob, Grep, Task, Bash, Write, Edit
argument-hint: <issue-description>
model: sonnet
---

**Goal**: Enter troubleshoot mode to diagnose and resolve development issues
**User Instructions**: $ARGUMENTS (optional)

## Tasks

1. Invoke @agent-troubleshooter to diagnose and resolve the issue
2. Report findings and resolution to the user

## Subagent Delegation

Delegate to `troubleshooter` agent with this prompt:

```
Diagnose and resolve the following development issue.

Issue description: $ARGUMENTS

Perform the following steps:

1. **Issue Analysis**
   - Understand the reported issue
   - Identify relevant files and code paths
   - Check error logs and stack traces if available

2. **Root Cause Investigation**
   - Trace the issue through the codebase
   - Identify the root cause
   - Document findings

3. **Resolution**
   - Propose a fix
   - Implement the fix if straightforward
   - Verify the fix resolves the issue

4. **Report**
   - Summarize the issue and root cause
   - Document the fix applied
   - Note any follow-up actions needed

Return a structured report with all findings and actions taken.
```

## Prohibited Tasks

- DO NOT make changes unrelated to the issue
- DO NOT skip investigation and jump to fixes
- DO NOT ignore error messages or stack traces
