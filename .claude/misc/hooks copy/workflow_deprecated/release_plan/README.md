# Release Plan

Hierarchical release plan state management for epics, features, user stories, tasks, acceptance criteria (ACs), and success criteria (SCs).

## Files

| File | Purpose |
|------|---------|
| `state.py` | File-locked state persistence for `project/state.json` |
| `getters.py` | Read-only access to project state values |
| `new_setters.py` | Write access to project state values |
| `checkers.py` | Boolean checks for completion and criteria status |
| `resolvers.py` | State transition logic (record completions, navigate hierarchy) |
| `utils.py` | Helper utilities for release plan operations |
| `project.py` | Project directory path utilities (`FeatureSubdir`) |
| `project/` | Project-specific state storage |

## Hierarchy

```
Epic (E001)
  -> Feature (F001)
    -> User Story (US-001)
      -> Task (T001, T002, ...)
      -> Acceptance Criteria (AC-001, AC-002, ...)
    -> Success Criteria (SC-001, SC-002, ...)
  -> Epic Success Criteria (SC-E001-001, ...)
```

## State Flow

1. Tasks are logged via `/log:task T001 completed`
2. When all tasks in a user story complete -> AC validation triggers
3. When all ACs met -> SC validation triggers
4. When all SCs met -> epic SC validation triggers

## Key Functions

- `load_project_state()` / `save_project_state()` - State persistence with file locking
- `get_current_epic_id()` / `get_current_feature_id()` / `get_current_user_story()` - Current context
- `record_completed_task()` / `record_met_ac()` / `record_met_sc()` - Record completions
- `is_task_completed()` / `is_ac_met()` / `is_sc_met()` - Status checks
- `resolve_user_story()` / `resolve_feature()` - Navigate hierarchy on completion
