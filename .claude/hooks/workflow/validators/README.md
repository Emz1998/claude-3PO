# Validators

Criteria validation enforcement and revision task management.

## Files

| File | Purpose |
|------|---------|
| `criteria_validator.py` | Detects pending AC/SC/epic SC validation based on completion status |
| `revision_manager.py` | Creates and tracks revision tasks when criteria validation fails |

## Validation Detection

`criteria_validator.py` checks whether validation is needed:

- `has_pending_ac_validation()` - All tasks in user story completed?
- `has_pending_sc_validation()` - All ACs in feature met?
- `has_pending_epic_sc_validation()` - All SCs in epic met?

## Revision Tasks

When the `validator` subagent finds unmet criteria, `revision_manager.py` creates revision tasks:

- ID format: `RT-{round}-{number}` (e.g., `RT-1-001`, `RT-2-003`)
- Stored in: `project/{version}/{epic_id}/{feature_id}/revisions/revision_tasks.json`
- Injected into `current_tasks` in project state
- Tracked like regular tasks by the release plan system

## Flow

1. `ReleasePlanTracker` sets `needs_ac_validation` flag after all tasks complete
2. `UserPromptHandler` detects the flag and sets `pending_validation`
3. `ContextInjector` injects validation context instructing deployment of `validator` subagent
4. Validator evaluates criteria and invokes `/log:ac AC-XXX met|unmet`
5. If unmet: `revision_manager.create_revision_tasks()` generates `RT-` prefixed tasks
6. Workflow continues with revision tasks until all criteria pass
