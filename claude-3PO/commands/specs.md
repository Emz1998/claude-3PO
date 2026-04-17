---
name: specs
description: Generate project specs through a 5-phase pipeline (vision, strategy, decision, architect, backlog)
allowed-tools: Bash, Read, Glob, Grep, Write, Agent, WebFetch, WebSearch, AskUserQuestion
argument-hint: <project-description>
model: haiku
---

Generate project specs for "$1" by following the phased pipeline below. Each phase is enforced by hook guardrails — the system will block tool calls that don't match the current phase.

> **Phase = Skill**. To transition between phases, invoke the corresponding `/skill` (e.g. `/vision`, `/strategy`, `/decision`, etc.).

## Workflow Initialization

!`python3 '${CLAUDE_PLUGIN_ROOT}/scripts/utils/initializer.py' specs ${CLAUDE_SESSION_ID} $ARGUMENTS`

## Instructions

- Follow the phased pipeline strictly. Guardrails enforce phase ordering.
- **Phases are skills.** Invoke `/vision`, `/strategy`, `/decision`, `/architect`, `/backlog` to enter each phase.
- All agents must be run in the **foreground** (not background).
- Agent counts must match the limits or the guardrail will block you.
- All output goes to `projects/docs/` directory.

## Pipeline

```
/vision → /strategy → /decision → /architect → /backlog
```

| Phase | Command | Who | Output |
|---|---|---|---|
| vision | `/vision` | Main agent | `product-vision.md` |
| strategy | `/strategy` | 3 Research agents (parallel) | Context for decisions |
| decision | `/decision` | Main agent | `decisions.md` |
| architect | `/architect` | Architect agent | `architecture.md` |
| backlog | `/backlog` | ProductOwner agent | `backlog.md` + `backlog.json` |

### 1. `/vision`

Ask the user 10 discovery questions via `AskUserQuestion`, then write `projects/docs/product-vision.md` using the product vision template.

### 2. `/strategy`

Launch 3 Research agents in parallel to research tech stack, architecture patterns, and security/DevOps.

### 3. `/decision`

Ask the user 10 technical decision questions via `AskUserQuestion`, then write `projects/docs/decisions.md`.

### 4. `/architect`

Launch 1 Architect agent to produce `projects/docs/architecture.md`. The agent's output is validated against the architecture template and auto-written.

### 5. `/backlog`

Launch 1 ProductOwner agent to produce `projects/docs/backlog.md`. The agent's output is validated against the backlog template and auto-written (including JSON conversion).

## Rules

- Follow phase order strictly. Guardrails enforce it.
- Do not skip phases unless in the `skip` list.
- Do not invoke agents beyond their max count.
- Validate work through the validators, not assumptions.

## References

- **Product vision template**: `${CLAUDE_PLUGIN_ROOT}/templates/product-vision.md`
- **Architecture template**: `${CLAUDE_PLUGIN_ROOT}/templates/architecture.md`
- **Backlog template**: `${CLAUDE_PLUGIN_ROOT}/templates/backlog.md`
- **Vision questions**: `${CLAUDE_PLUGIN_ROOT}/templates/visionize-questions.md`
- **Decision questions**: `${CLAUDE_PLUGIN_ROOT}/commands/decision_questions.md`
