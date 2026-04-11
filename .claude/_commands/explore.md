---
name: explore
description: Phase 1 — Launch 3 parallel Explore agents to analyze the codebase from different angles.
argument-hint: <topic-or-area-to-explore>
model: sonnet
---

**Phase 1: Explore Codebase**

Launch 3 `Explore` agents **in parallel** (single message, 3 Agent tool calls).

## Agent Focus Areas

1. **Agent 1 — Project structure & configuration**: Analyze the project layout, build config, entry points, and key directories. Identify the critical files and their relationships.

2. **Agent 2 — Git activity & dependencies**: Analyze recent git history, dependency graph, and package versions. Identify active areas and potential risks.

3. **Agent 3 — Implementation state & technical health**: Analyze code quality, test coverage, TODOs, and technical debt. Identify areas needing attention.

## Instructions

1. Launch all 3 agents in a **single message**
2. Each agent should focus on its assigned area
3. Agents run in foreground — wait for all to complete

## Completion

Once all agents complete, synthesize findings and advance to the next phase.
