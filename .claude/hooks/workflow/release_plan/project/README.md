# Project

Project-specific state storage for the release plan.

## Files

| File | Purpose |
|------|---------|
| `state.json` | Current release plan state (epic, feature, user story, tasks, ACs, SCs) |

## State Structure

```json
{
  "current_epic_id": "E001",
  "current_feature_id": "F001",
  "current_user_story": "US-001",
  "current_tasks": {"T001": "completed", "RT-1-001": "not_started"},
  "current_acs": {"AC-001": "unmet"},
  "current_scs": {"SC-001": "unmet"},
  "completed_tasks": ["T000"],
  "completed_user_stories": [],
  "completed_features": [],
  "completed_epics": [],
  "met_acs": [],
  "met_scs": [],
  "met_epic_scs": []
}
```

This file is managed by `release_plan/state.py` with file locking for safe concurrent access.
