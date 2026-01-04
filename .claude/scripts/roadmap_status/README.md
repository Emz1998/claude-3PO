# Roadmap Status Script

Updates task, AC, or SC status in roadmap.json with support for batch processing.

## Usage

**Single item:**

```bash
python3 roadmap_status.py T001 in_progress
python3 roadmap_status.py AC-001 met
python3 roadmap_status.py SC-001 met
```

**Multiple items (range):**

```bash
python3 roadmap_status.py T001-T007 in_progress
python3 roadmap_status.py AC-001-AC-005 met
python3 roadmap_status.py SC-001-SC-003 met
```

**Multiple items (list):**

```bash
python3 roadmap_status.py T001 T003 T005 in_progress
python3 roadmap_status.py T001,T003,T005 completed
python3 roadmap_status.py AC-001 AC-003 met
```

## Arguments

**Item ID formats:**

- Task: `TXXX` (e.g., T001)
- Acceptance Criteria: `AC-XXX` (e.g., AC-001)
- Success Criteria: `SC-XXX` (e.g., SC-001)
- Range: `T001-T007`, `AC-001-AC-005`, `SC-001-SC-003`

**Status values:**

- Task: `not_started`, `in_progress`, `completed`, `blocked`
- AC/SC: `met`, `unmet`

## Features

- Auto-detects item type from ID format
- Supports batch processing (ranges and lists)
- All items in a command must be the same type
- Continue on error (valid items updated, failures reported)
- Validates status based on item type
- Blocks AC update if parent task is not `in_progress`
- Blocks SC update if milestone tasks are not all `completed`
- Blocks task `in_progress`/`completed` if dependencies incomplete
- Auto-resolves milestone, phase, and project status
- Updates current pointer and summary counts

## Roadmap Path

Reads from `project/{version}/release-plan/roadmap.json` where version comes from `project/product/PRD.json`.
