---
name: review-test
description: Create implementation plan by delegating to strategic-planner and consulting-expert agents
allowed-tools: Read, Write, Glob, Grep, Task
argument-hint: <instructions>
model: sonnet
---

trigger @test-reviewer agent to review the tests

1. Instruct the subagent to read the test file at `project/v0.1.0/PH-001_[Foundation - Environment and Data Models]/MS-001_[Project Setup and Configuration]/tests/test-summary_20260130_05.md`
2. Instruct the subagent to write "Review Test" to the file `project/v0.1.0/PH-001_[Foundation - Environment and Data Models]/MS-001_[Project Setup and Configuration]/tests/test-quality-report_20260130_06.md`
