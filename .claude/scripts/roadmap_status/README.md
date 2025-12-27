# Roadmap Status Scripts

Scripts for querying and updating roadmap.json status.

## Scripts

### 1. roadmap_status.py

**Purpose**: Update task, AC, or SC status in roadmap.json

```bash
# Task status updates
python3 roadmap_status.py T001 in_progress
python3 roadmap_status.py T002 completed
python3 roadmap_status.py T003 blocked

# Acceptance criteria updates
python3 roadmap_status.py AC-001 met
python3 roadmap_status.py AC-002 unmet

# Success criteria updates
python3 roadmap_status.py SC-001 met
python3 roadmap_status.py SC-002 unmet
```

**Arguments**:

- `item_id` - Item ID format:
  - Task: `TXXX` (e.g., T001)
  - Acceptance Criteria: `AC-XXX` (e.g., AC-001)
  - Success Criteria: `SC-XXX` (e.g., SC-001)
- `status` - New status:
  - Task: `not_started`, `in_progress`, `completed`, `blocked`
  - AC/SC: `met`, `unmet`

**Features**:

- Auto-detects item type from ID format
- Validates status based on item type
- Blocks AC update if parent task is not `in_progress`
- Blocks SC update if milestone tasks are not all `completed`
- Blocks task `in_progress`/`completed` if dependencies incomplete
- Auto-resolves milestone, phase, and project status
- Updates current pointer and summary counts

### 2. roadmap_query.py

**Purpose**: Query roadmap.json for project information

```bash
# Named queries
python3 roadmap_query.py todo         # Current tasks with full context
python3 roadmap_query.py version      # Project version and summary
python3 roadmap_query.py current      # Current focus
python3 roadmap_query.py phases       # List all phases
python3 roadmap_query.py milestones   # List all milestones
python3 roadmap_query.py tasks        # List all tasks
python3 roadmap_query.py blockers     # Show blockers
python3 roadmap_query.py metadata     # Roadmap metadata

# Filtered queries
python3 roadmap_query.py milestones PH-001   # Milestones in phase
python3 roadmap_query.py tasks MS-001        # Tasks in milestone
python3 roadmap_query.py acs T001            # ACs for task
python3 roadmap_query.py scs MS-001          # SCs for milestone

# Specific item queries (by ID)
python3 roadmap_query.py PH-001   # Phase details
python3 roadmap_query.py MS-001   # Milestone details
python3 roadmap_query.py T001     # Task details
python3 roadmap_query.py AC-001   # AC details
python3 roadmap_query.py SC-001   # SC details
```

**Query Types**:

- `todo` - Current tasks with full context (phase, milestone, feature, deps, ACs, SCs)
- `version` - Project name, version, status, summary
- `current` - Current phase/milestone/task focus
- `phases` - All phases with completion counts
- `milestones` - All milestones (optional: filter by phase ID)
- `tasks` - All tasks (optional: filter by milestone ID)
- `acs` - Acceptance criteria (optional: filter by task ID)
- `scs` - Success criteria (optional: filter by milestone ID)
- `blockers` - Blocked tasks and unmet criteria
- `metadata` - Last updated, schema version

**ID Patterns**:

- `PH-XXX` - Phase (e.g., PH-001)
- `MS-XXX` - Milestone (e.g., MS-001)
- `TXXX` - Task (e.g., T001)
- `AC-XXX` - Acceptance Criteria (e.g., AC-001)
- `SC-XXX` - Success Criteria (e.g., SC-001)

## Roadmap Path

Scripts read from `project/{version}/release-plan/roadmap.json` where version is read from `project/product/PRD.json`.

## Status Indicators

Output uses visual indicators:

- `[✓]` - completed/met
- `[~]` - in_progress
- `[ ]` - not_started/pending/unmet
- `[!]` - blocked
