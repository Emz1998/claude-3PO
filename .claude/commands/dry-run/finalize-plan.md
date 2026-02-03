---
name: finalize-plan
description: Create implementation plan by delegating to strategic-planner and consulting-expert agents
allowed-tools: Read, Write, Glob, Grep, Task
argument-hint: <instructions>
model: sonnet
---

trigger @planner agent to finalize the implementation plan

1. Instruct the subagent to read the initial plan at `project/v0.1.0/PH-001_[Foundation - Environment and Data Models]/MS-001_[Project Setup and Configuration]/plan-consultation_20260130_03.md`
2. Instruct the subagent to write "Final Plan" to the file `project/v0.1.0/PH-001_[Foundation - Environment and Data Models]/MS-001_[Project Setup and Configuration]/plans/final-plan_20260130_04.md` if prompt specify final plan.
