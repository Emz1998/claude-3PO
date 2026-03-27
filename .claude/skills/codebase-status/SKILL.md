---
name: codebase-status
description: Explore the codebase and generate a comprehensive status report. Use when user wants to understand project state, recent changes, dependencies, or technical debt. Triggers include "codebase status", "project status", "explore codebase", or "what's the state of the project".
argument-hint: <additional-context>
model: sonnet
allowed-tools: Read, Glob, Grep, Bash
---

**Goal**: Explore the codebase and generate a comprehensive status report by delegating to the codebase-explorer agent

**User Instructions**: $ARGUMENTS (optional)

## Tasks

1. Invoke @agent-codebase-explorer with the analysis prompt below
2. Report the status report to the user

## Subagent Delegation

Delegate to `codebase-explorer` agent with this prompt:

```
Perform a comprehensive codebase status analysis.

Additional context from user: $ARGUMENTS

Analyze and report on:

1. **Project Structure Overview**
   - Directory organization and key folders
   - Configuration files and their purposes
   - Build and development tooling

2. **Git Status & Recent Activity**
   - Current branch and staging state
   - Recent commits (last 10-15)
   - Modified, added, and deleted files

3. **Dependencies & Stack**
   - Core dependencies with versions
   - Development dependencies
   - Potential version conflicts or outdated packages

4. **Current Implementation State**
   - Work-in-progress features
   - Incomplete or pending changes
   - Technical debt indicators

5. **Technical Constraints & Considerations**
   - Configuration constraints
   - Integration points
   - Identified issues or warnings

Return a structured markdown report with all findings.
```

## Prohibited Tasks

- DO NOT modify any source code files
- DO NOT run build scripts or test suites
- DO NOT expose sensitive information from environment files
- DO NOT skip the codebase-explorer agent delegation
