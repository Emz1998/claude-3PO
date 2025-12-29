# Status JSON Template Schema (v1.0)

Schema for `project/status.json` - single source of truth for project progress tracking.

---

## Full Schema

```json
{
  "project": {
    "name": "Project Name",
    "version": "0.1.0",
    "target_release": "2026-01-01",
    "status": "not_started"
  },

  "specs": {
    "prd": { "status": "not_started", "path": "specs/prd.md" },
    "tech": { "status": "not_started", "path": "specs/tech.md" },
    "ux": { "status": "not_started", "path": "specs/ux.md" }
  },

  "summary": {
    "phases": { "total": 0, "completed": 0 },
    "milestones": { "total": 0, "completed": 0 },
    "tasks": { "total": 0, "completed": 0 }
  },

  "current": {
    "phase": null,
    "milestone": null,
    "task": null
  },

  "phases": {
    "1": {
      "id": "phase-1",
      "name": "Foundation - Environment Setup",
      "status": "not_started",
      "milestones": {
        "MS-001": {
          "name": "Environment Setup",
          "goal": "Next.js 15 + React 19 development environment fully configured",
          "parallel": false,
          "parallel_with": [],
          "dependencies": [],
          "status": "not_started",
          "tasks": {
            "T001": {
              "description": "Initialize Next.js 15.1 project with App Router",
              "priority": true,
              "subagent_delegation": false,
              "dependencies": [],
              "subagents": [],
              "status": "not_started"
            },
            "T002": {
              "description": "Configure Tailwind CSS 4.1 with Shadcn UI theme tokens",
              "priority": true,
              "subagent_delegation": false,
              "subagents": [],
              "dependencies": [],
              "status": "not_started"
            }
          },
          "acceptance_criteria": [
            {
              "id": "AC-001",
              "description": "npm run dev starts without errors",
              "met": false
            },
            {
              "id": "AC-002",
              "description": "npm run build completes successfully",
              "met": false
            }
          ]
        }
      }
    }
  },

  "metadata": {
    "last_updated": "2025-12-18T00:00:00Z",
    "schema_version": "1.0.0"
  }
}
```

---

## Field Definitions

**Project**

- `name` - Project display name
- `version` - Current version (semver)
- `target_release` - Target release date (ISO 8601)
- `status` - `not_started` | `in_progress` | `completed` | `blocked`

**Specs**

- `status` - `not_started` | `in_progress` | `completed`
- `path` - Relative path to spec file

**Summary** - Aggregate counts for quick status overview

- `total` - Total count
- `completed` - Completed count

**Current** - Tracks active work

- `phase` - Current phase number (e.g., `"1"`) or `null`
- `milestone` - Current milestone ID (e.g., `"MS-001"`) or `null`
- `task` - Current task ID (e.g., `"T001"`) or `null`

**Phase**

- `id` - Unique phase identifier
- `name` - Phase name/description
- `status` - Status enum
- `milestones` - Map of milestone IDs to milestone objects

**Milestone**

- `name` - Milestone name
- `goal` - What this milestone achieves
- `status` - Status enum
- `tasks` - Map of task IDs to task objects
- `acceptance_criteria` - List of acceptance criteria objects
- `verification` - List of verification steps (strings)

**Task**

- `description` - What the task accomplishes
- `priority` - `true` if marked `[P]` (blocking/critical path)
- `subagent` - `true` if marked `[SA]` (can delegate to subagent)
- `status` - Status enum
- `refs` - Spec references (e.g., `["Tech Specs Section 3"]`)

**Acceptance Criteria**

- `id` - Unique identifier (e.g., `AC-001`)
- `description` - What must be true for acceptance
- `met` - Boolean whether criteria satisfied

---

## Status Enum Values

- `not_started` - Work has not begun
- `in_progress` - Actively being worked on
- `completed` - Successfully finished
- `blocked` - Cannot proceed (dependency/issue)

---

## Task Flags

**Priority `[P]`**

- Critical path tasks that block other work
- Must complete before dependent tasks start
- Set `"priority": true`

**Subagent `[SA]`**

- Tasks eligible for parallel execution via subagents
- Can be delegated to specialized agents
- Set `"subagent": true`

---

## ID Formats

- **Task IDs** - `T###` (e.g., T001, T011, T100)
- **Milestone IDs** - `MS-###` (e.g., MS-001, MS-002)
- **Phase keys** - Simple integers as strings (e.g., `"1"`, `"2"`)
- **Acceptance Criteria IDs** - `AC-###` (e.g., AC-001)

---

## Usage Notes

1. Update `summary` counts when tasks/milestones complete
2. Update `current` to reflect active work
3. Update `metadata.last_updated` on every change
4. Keep `refs` populated for traceability to specs
