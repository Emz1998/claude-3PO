---
name: discuss
description: Interactive discussion session with AI agents for implementation strategy and decision-making
allowed-tools: Bash(python:*)
model: opus
---

**Goal**: Gather multiple opinions to explore implementation strategies and make decisions for the current task

## Workflow

### Phase 1: Context Gathering

- Deploy @agent-consultant to discuss about how to implement the current task in the roadmap.
- Call @gpt-manager to get second opinion about the implementation strategy.
- Call @gemini-manager to get third opinion about the implementation strategy.
