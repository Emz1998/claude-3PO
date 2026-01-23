---
name: explore
description: Dry run of the explore phase
allowed-tools: Read, Glob, Grep, Task
argument-hint: <context>
model: sonnet
---

**Goal**: Dry run of the explore phase

## Workflow

1. Invoke @agent-codebase-explorer subagent to write the todays date to the specified file path
2. After writing, exit right away without doing any work. This is a test dry-run.
