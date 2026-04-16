---
name: backlog
description: Phase 5 — Launch ProductOwner agent to produce backlog.md + backlog.json (validated + auto-written)
argument-hint: <backlog-focus>
model: sonnet
---

**Phase 5: Backlog**

Launch 1 `ProductOwner` agent to produce the product backlog.

## Instructions

1. Read all previous docs: `projects/docs/product-vision.md`, `projects/docs/decisions.md`, `projects/docs/architecture.md`
2. Read the backlog template at `${CLAUDE_PLUGIN_ROOT}/skills/backlog/template/backlog.md`
3. Launch the **ProductOwner** agent with a prompt to:
   - Read the vision, decisions, and architecture docs
   - Follow the backlog template exactly
   - Create epics broken into user stories (US), technical stories (TS), spikes (SK), and bugs (BG)
   - Produce the complete backlog markdown as the agent's final response
4. The agent's output is **validated** against the backlog schema at `SubagentStop`
5. If valid, the document is **auto-written** to:
   - `projects/docs/backlog.md` (markdown)
   - `projects/docs/backlog.json` (auto-converted from markdown)
6. If invalid, the agent report is **blocked** — re-invoke with corrections

## Agent Prompt

The agent should produce the complete backlog as its final message. The guardrail will:
- Validate metadata (Project, Last Updated)
- Validate section structure (Priority Legend, ID Conventions, Stories)
- Validate each story (ID format, description, priority, acceptance criteria, blockquote format)
- Auto-convert to JSON and write both files on success

Allowed: Read, Glob, Grep.

## Completion

Phase completes when the backlog is validated and both files are written.
