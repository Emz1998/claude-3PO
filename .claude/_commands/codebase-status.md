---
name: codebase-status
description: Phase 1 — Explore the codebase with 3 parallel codebase-explorer agents, each focused on a different critical area
argument-hint: <story-or-task-description>
model: sonnet
---

**Phase 1: Codebase Exploration**

Launch 3 `codebase-explorer` agents **in parallel** (single message, 3 Agent tool calls). Each agent explores a different area of the codebase relevant to the current task.

## Agent Focus Areas

Divide exploration across these dimensions (adapt to the task at hand):

1. **Agent 1 — Core domain / business logic**: Entry points, main modules, core data models, key functions related to the task
2. **Agent 2 — Infrastructure / configuration**: Dependencies, config files, environment setup, build system, existing utilities and helpers
3. **Agent 3 — Tests & patterns**: Existing test structure, naming conventions, coding patterns, similar prior implementations

## Instructions

1. Read the task description (from `$ARGUMENTS` or prior context)
2. Determine what areas of the codebase are most relevant
3. Launch all 3 agents in a **single message** with 3 parallel Agent tool calls
4. Each agent prompt should specify: what to explore, what questions to answer, what files to surface

## Each Agent Prompt Should Cover

- Where to look (directories, file patterns)
- What specific questions to answer (e.g. "how is auth currently handled?")
- What to report: relevant file paths, function signatures, patterns found

## Completion

Once all 3 agents complete, summarize key findings for the next phase (`/research`).
