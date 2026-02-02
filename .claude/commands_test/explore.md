---
name: explore
description: Dry run of the explore phase
allowed-tools: Read, Glob, Grep, Task
argument-hint: <context>
model: sonnet
---

Trigger @codebase-explorer agent to explore the codebase

1. Instruct it to write only the word "Codebase Status" to the file `project/v0.1.0/PH-001_[Foundation - Environment and Data Models]/MS-001_[Project Setup and Configuration]/codebase-status/codebase-status_20260130_01.md`
2. File should only contain the word "Codebase Status" and nothing else.
