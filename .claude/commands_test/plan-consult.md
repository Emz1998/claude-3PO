---
name: plan-consult
description: Create implementation plan by delegating to strategic-planner and consulting-expert agents
allowed-tools: Read, Write, Glob, Grep, Task
argument-hint: <instructions>
model: sonnet
---

trigger @plan-consultant agent to review the plan

1. Instruct the subagent to read the initial plan at `project/v0.1.0/PH-001_[Foundation - Environment and Data Models]/MS-001_[Project Setup and Configuration]/plans/initial-plan_20260130_02.md`
2. Instruct the subagent to write "Plan Consultation" to the file `project/v0.1.0/PH-001_[Foundation - Environment and Data Models]/MS-001_[Project Setup and Configuration]/plans/plan-consultation_20260130_03.md` if prompt specify plan consultation.
