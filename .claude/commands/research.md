---
name: research
description: Phase 2 — Research strategies and latest documentation with 2 parallel research-specialist agents
argument-hint: <topic-or-task>
model: sonnet
---

**Phase 2: Research**

Launch 2 `research-specialist` agents **in parallel** (single message, 2 Agent tool calls).

## Agent Focus Areas

1. **Agent 1 — Implementation strategies**: Research best practices, architectural patterns, and proven approaches for the task at hand. Compare trade-offs. Identify what the industry recommends.

2. **Agent 2 — Latest documentation**: Fetch and summarize the latest official documentation for all relevant libraries, frameworks, and APIs involved in this task. Focus on recent versions and any breaking changes.

## Instructions

1. Identify the technologies and patterns relevant to the current task
2. Launch both agents in a **single message**
3. Agent 1 prompt: focus on strategies, patterns, and implementation trade-offs
4. Agent 2 prompt: focus on official docs, API references, version-specific guidance

## Completion

Once both agents complete, synthesize findings for the `/decision` phase.
