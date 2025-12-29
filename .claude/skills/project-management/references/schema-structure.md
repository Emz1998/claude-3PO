# Roadmap JSON Schema

**Version:** 1.0.0

This document defines the structure for `roadmap.json` files used in project execution tracking.

---

## Top-Level Structure

```json
{
  "name": "string",
  "version": "string",
  "target_release": "string (ISO date)",
  "status": "string",
  "phases": [],
  "current": {},
  "summary": {},
  "metadata": {}
}
```

- **name**: Project name
- **version**: Version being tracked (e.g., "0.1.0")
- **target_release**: Target release date (ISO format)
- **status**: Overall status: `not_started`, `in_progress`, `completed`
- **phases**: Sequential execution phases
- **current**: Active phase, milestone, and task IDs
- **summary**: Computed counts for phases, milestones, tasks
- **metadata**: Schema version and last update timestamp

---

## Phase

Phases run **sequentially**. Order in array determines execution order.

```json
{
  "id": "PH-NNN",
  "name": "string",
  "status": "string",
  "checkpoint": "boolean",
  "milestones": []
}
```

- **id**: Unique identifier (pattern: `PH-NNN`)
- **name**: Phase name
- **status**: `not_started`, `in_progress`, `completed`
- **checkpoint**: Set to true for phases that are checkpoints.
- **milestones**: Milestones within this phase (run in parallel)

---

## Milestone

Milestones within a phase run **in parallel**. One feature per milestone (1:1 mapping).

```json
{
  "id": "MS-NNN",
  "feature": "FNNN",
  "name": "string",
  "goal": "string",
  "status": "string",
  "dependencies": [],
  "mcp_servers": [],
  "success_criteria": [],
  "tasks": []
}
```

- **id**: Unique identifier (pattern: `MS-NNN`)
- **feature**: Reference to feature in product.json (pattern: `FNNN`)
- **name**: Milestone name
- **goal**: What this milestone achieves
- **status**: `not_started`, `in_progress`, `completed`
- **dependencies**: MS-IDs that must complete first
- **mcp_servers**: List of MCP servers to use for the milestone. If no MCP needed, leave empty.
- **success_criteria**: Feature-level success verification
- **tasks**: Tasks to complete this milestone

---

## Success Criteria (Milestone Level)

References SC from product.json. Verifies feature-level outcomes.

```json
{
  "id": "SC-NNN",
  "description": "string",
  "status": "string (met|unmet)"
}
```

- **id**: SC-NNN format
- **description**: Description of the success criteria
- **status**: `met` or `unmet` (string)

---

## Task

Individual work items that satisfy acceptance criteria.

```json
{
  "id": "TNNN",
  "description": "string",
  "status": "string",
  "parallel": "boolean",
  "owner": "string",
  "test_strategy": "string (TDD|TA)",
  "dependencies": [],
  "acceptance_criteria": []
}
```

- **id**: Unique identifier (pattern: `TNNN`)
- **description**: What the task accomplishes
- **status**: `not_started`, `in_progress`, `completed`
- **parallel**: `true` if can run in parallel with other tasks, otherwise `false`
- **owner**: Agent responsible (from `.claude/agents/engineers/` or `main-agent`)
- **test_strategy**: `TDD` or `TA` where TDD is Test-Driven Development and TA is Test-After Development.
- **dependencies**: T-IDs that must complete first
- **acceptance_criteria**: AC references from product.json

---

## Acceptance Criteria (Task Level)

References AC from product.json. Verifies user story behaviors.

```json
{
  "id": "AC-NNN",
  "description": "string",
  "status": "met|unmet"
}
```

- **id_reference**: AC-ID from product.json user stories
- **status**: `met` or `unmet`

---

## Current

Tracks the active phase, milestone, and task.

```json
{
  "phase": "PH-NNN",
  "milestone": "MS-NNN",
  "task": "TNNN"
}
```

- **phase**: Currently active phase ID
- **milestone**: Currently active milestone ID
- **task**: Currently active task ID

---

## Summary

Computed counts updated after every mutation.

```json
{
  "phases": {
    "total": 0,
    "pending": 0,
    "completed": 0
  },
  "milestones": {
    "total": 0,
    "pending": 0,
    "completed": 0
  },
  "tasks": {
    "total": 0,
    "pending": 0,
    "completed": 0
  }
}
```

- **total**: Total count
- **pending**: Count where status != `completed`
- **completed**: Count where status == `completed`

---

## Metadata

```json
{
  "last_updated": "ISO 8601 datetime",
  "schema_version": "1.0.0"
}
```

- **last_updated**: Last modification timestamp
- **schema_version**: Schema version for compatibility

---

## ID Patterns

- **Phase**: `PH-NNN` (e.g., PH-001)
- **Milestone**: `MS-NNN` (e.g., MS-001)
- **Task**: `TNNN` (e.g., T001)
- **Success Criteria**: `SC-NNN` (e.g., SC-001, from product.json)
- **Acceptance Criteria**: `AC-NNN` (e.g., AC-001, from product.json)
- **Feature**: `FNNN` (e.g., F001, from product.json)

---

## Completion Logic

- **Task**: status = `completed` AND all acceptance_criteria.status = `met`
- **Milestone**: All tasks complete AND all success_criteria.status = `met`
- **Phase**: All milestones complete
- **Roadmap**: All phases complete

---

## Status Values

- **not_started**: Work has not begun
- **in_progress**: Currently being worked on
- **completed**: Work finished and verified

---

## Criteria Status Values

- **met**: Criteria has been satisfied
- **unmet**: Criteria has not been satisfied
