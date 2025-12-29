# Context Hooks Module

Hook scripts for injecting context information into Claude sessions.

## Files

**roadmap_context.py**

- Hook Event: `SessionStart`
- Injects current roadmap context into session
- Writes context to `project/{version}/todos/todo_{date}_{session_id}.md`
- Reads from `project/{version}/release-plan/roadmap.json`
- Enriches AC/SC with full context from `project/product/PRD.json`

## Context Output

The hook provides:

- Project name, version, target release
- Progress summary (phases, milestones, tasks)
- Current phase with status
- Current milestone with feature, goal, success criteria (with full description from PRD)
- Current task with owner, dependencies, acceptance criteria (with full criteria text from PRD)
- Pending tasks in current milestone
- Blockers (unmet AC/SC with full context from PRD)

## PRD Integration

The hook loads `project/product/PRD.json` to provide full context for:

- **Acceptance Criteria (AC)**: Shows the full criteria text from user stories
- **Success Criteria (SC)**: Shows title and description from feature definitions

This enrichment applies to:
1. Milestone success criteria display
2. Task acceptance criteria display
3. Blockers section (unmet AC/SC)

## File Output

Creates: `project/{version}/todos/todo_{YYYY-MM-DD}_{session_id}.md`

- Directory created automatically if missing
- Session ID truncated to first 8 characters
- One file per session start

## Dependencies

- `utils` module from `.claude/hooks/utils/`
- `utils.roadmap` for roadmap operations
- `utils.load_json` for PRD loading
- Python 3.10+
