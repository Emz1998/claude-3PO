---
name: plan
description: Create implementation plan by delegating to strategic-planner and consulting-expert agents
allowed-tools: Read, Write, Glob, Grep, Task
argument-hint: <instructions>
model: sonnet
---

trigger @planner agent to create the implementation plan

1. Instruct the subagent to read the codebase status at `project/v0.1.0/PH-001_[Foundation - Environment and Data Models]/MS-001_[Project Setup and Configuration]/exploration/codebase-status_20260130_01.md`
2. Instruct the subagent to write "Initial Plan" to the file `project/v0.1.0/PH-001_[Foundation - Environment and Data Models]/MS-001_[Project Setup and Configuration]/plans/initial-plan_20260130_02.md` if prompt specify initial plan.
