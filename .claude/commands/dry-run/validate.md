---
name: validate
description: Validate the implementation
allowed-tools: Read, Write, Glob, Grep, Task
argument-hint: <instructions>
model: sonnet
---

trigger @validator agent to validate the code

1. Instruct the subagent to write "Validation Report" to the file `project/v0.1.0/PH-001_[Foundation - Environment and Data Models]/MS-001_[Project Setup and Configuration]/reports/validation_report_20260130_10.md`
