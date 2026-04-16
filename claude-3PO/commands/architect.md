---
name: architect
description: Phase 4 — Launch Architect agent to produce architecture.md (validated + auto-written)
argument-hint: <architecture-focus>
model: sonnet
---

**Phase 4: Architecture**

Launch 1 `Architect` agent to produce the architecture document.

## Instructions

1. Read `projects/docs/product-vision.md` and `projects/docs/decisions.md` for context
2. Read the architecture template at `${CLAUDE_PLUGIN_ROOT}/skills/architect/templates/architecture.md`
3. Launch the **Architect** agent with a prompt to:
   - Read the product vision and decisions docs
   - Follow the architecture template exactly
   - Produce a complete architecture document as the agent's final response
4. The agent's output is **validated** against the architecture template at `SubagentStop`
5. If valid, the document is **auto-written** to `projects/docs/architecture.md`
6. If invalid, the agent report is **blocked** — re-invoke with corrections

## Agent Prompt

The agent should produce the complete architecture document as its final message. The guardrail will:
- Validate required metadata (Project Name, Version, Date, Author(s), Status)
- Validate all 13 required sections and subsections
- Auto-write to `projects/docs/architecture.md` on success

Allowed: Read, Glob, Grep, WebFetch, WebSearch.

## Completion

Phase completes when the architecture document is validated and written.
