## Context

During `task-create` phase, Claude creates tasks freely via `TaskCreate`. Currently `task_guard.py` validates at `TaskCreated` time that the subject starts with the story ID prefix — but there's no validation that each Claude task maps to a real project task.

The goal: validate at **PreToolUse TaskCreate** time that each task includes `metadata.parent_task_id` and `metadata.parent_task_title`, and that these match a real task from `project_manager.py view <story-id> --tasks --json`. Build a task map in `state.json` tracking which project tasks have been covered.

## Approach

### Step 1: Add PreToolUse TaskCreate handler in `guardrail.py`

In `_dispatch()`, add a case for `tool == "TaskCreate"` under `PreToolUse`:

```python
if tool == "TaskCreate":
    return task_guard.validate(hook_input, store)
```

This runs **before** the existing `TaskCreated` event handler (which is post-creation).

### Step 2: Rewrite `task_guard.validate()` for PreToolUse

File: `.claude/hooks/workflow/guards/task_guard.py`

New validation logic:
1. If not `task-create` phase or no `story_id` in state → allow (bypass)
2. Extract `parent_task_id` and `parent_task_title` from `tool_input.metadata`
3. If either is missing → **block** with message explaining required metadata
4. Fetch project tasks: call `project_manager.py view <story-id> --tasks --json` (cache result in `state.project_tasks_cache` to avoid repeated subprocess calls)
5. Look up `parent_task_id` in cached tasks — if not found → **block**
6. Verify `parent_task_title` matches the found task's `title` — if mismatch → **block**
7. Allow, and record the mapping in `state.task_map`

### Step 3: Task mapping design in `state.json`

```json
{
  "tasks": [
    {
      "id": 1,
      "subject": "Feature importance analysis documented in decisions.md",
      "description": "Perform feature importance analysis and document findings",
      "status": "pending",
      "subtasks": [
        {
          "id": 1,
          "subject": "Analyze feature correlations",
          "description": "Run correlation analysis on all features...",
          "status": "pending"
        }
      ]
    },
    {
      "id": 2,
      "subject": "Recommendation includes feature set with pros/cons",
      "description": "Develop feature set recommendations with trade-offs",
      "status": "pending",
      "subtasks": []
    }
  ]
}
```

- `tasks`: populated from `project_manager.py view <story-id> --tasks --json` on first TaskCreate (cached for subsequent calls). Each entry is a project task.
- `tasks[].subtasks`: Claude-created tasks that reference this parent. Appended on each successful TaskCreate validation.
- `metadata.parent_task_id` maps to `tasks[].id`, `metadata.parent_task_title` maps to `tasks[].subject`

### Step 4: Record subtask in `task_guard.validate()`

On successful validation, append a subtask entry to the matching parent's `subtasks` array:

```python
subtask = {
    "id": len(parent_task["subtasks"]) + 1,
    "subject": tool_input.get("subject", ""),
    "description": tool_input.get("description", ""),
    "status": "pending",
}
parent_task["subtasks"].append(subtask)
```

The recorder's existing `record_task_created()` keeps incrementing `tasks_created` count — no changes needed there.

### Step 5: Handle `TaskCompleted` event — update subtask status

Add `validate_completed()` in `task_guard.py` to handle `TaskCompleted` events:

1. Receive `task_id` and `task_subject` from hook input
2. Find the matching subtask in `state.tasks[].subtasks[]` by subject match
3. Update its `status` from `"pending"` to `"completed"`
4. Save state

When updating a subtask to `"completed"`, check if **all** subtasks under that parent are now `"completed"`. If so, set the parent task's `status` to `"completed"` as well.

Wire it in `guardrail.py` `_dispatch()`:
```python
if event == "TaskCompleted":
    return task_guard.validate_completed(hook_input, store)
```

Register `TaskCompleted` hook in `.claude/settings.local.json` — currently only `TaskCreated` is registered (line 116). Add a `TaskCompleted` entry pointing to the guardrail dispatcher, same pattern as `TaskCreated`.

`TaskCompleted` hook input shape:
```json
{
  "hook_event_name": "TaskCompleted",
  "task_id": "task-001",
  "task_subject": "Implement user authentication",
  "task_description": "Add login and signup endpoints"
}
```

### Step 6: Remove old subject-prefix validation

The current `task_guard.py` checks `subject.startswith(f"{story_id}:")`. This is replaced by the metadata-based validation. Remove the old logic.

## Files to Modify

| File | Change |
|------|--------|
| `.claude/hooks/workflow/guards/task_guard.py` | Rewrite `validate()` — metadata validation, project task lookup, cache, subtask recording |
| `.claude/hooks/workflow/guardrail.py` | Add `TaskCreate` in PreToolUse + `TaskCompleted` event dispatch |
| `.claude/hooks/workflow/tests/test_task_guard.py` | Rewrite tests for PreToolUse TaskCreate input shape + new validation cases |
| `.claude/hooks/workflow/dry_runs/implement_dry_run.py` | Replace `task_created_payload` with PreToolUse TaskCreate payload + update assertions |
| `.claude/hooks/workflow/recorder.py` | No changes needed — keep `record_task_created()` for counter |
| `.claude/settings.local.json` | Add `TaskCompleted` hook registration pointing to guardrail dispatcher |

### Step 7: Update tests — `tests/test_task_guard.py`

Rewrite all test cases to use PreToolUse TaskCreate input shape instead of TaskCreated.

Replace `task_created_hook()` helper with `task_create_hook()` that builds:
```python
{
    "hook_event_name": "PreToolUse",
    "tool_name": "TaskCreate",
    "tool_input": {
        "subject": "...",
        "description": "...",
        "metadata": {
            "parent_task_id": 1,
            "parent_task_title": "..."
        }
    },
    ...
}
```

New test cases:
- `test_missing_parent_task_id_blocked` — no `parent_task_id` in metadata → block
- `test_missing_parent_task_title_blocked` — no `parent_task_title` in metadata → block
- `test_missing_metadata_blocked` — no metadata at all → block
- `test_valid_parent_task_allowed` — id + title match cached project task → allow
- `test_parent_task_id_not_in_project_blocked` — id not found → block
- `test_parent_task_title_mismatch_blocked` — id found but title doesn't match → block
- `test_subtask_recorded_on_allow` — after allow, subtask appended to parent's subtasks
- `test_cache_populated_on_first_call` — `tasks` populated in state from project_manager
- `test_cache_reused_on_second_call` — second call doesn't re-run subprocess
- `test_workflow_inactive_allows_all` — keep existing
- `test_outside_task_create_phase_allows_all` — keep existing
- `test_no_story_id_allows_all` — keep existing

TaskCompleted test cases:
- `test_task_completed_updates_subtask_status` — subtask status changes to "completed"
- `test_task_completed_no_match_allows` — unknown subject still allows (no block on completion)
- `test_task_completed_workflow_inactive_allows` — no-op when workflow inactive
- `test_all_subtasks_completed_resolves_parent` — when last subtask completes, parent status becomes "completed"
- `test_partial_subtasks_completed_parent_stays_pending` — parent stays "pending" if some subtasks still pending

Remove old tests: `test_valid_subject_with_story_prefix_allowed`, `test_invalid_subject_without_story_prefix_blocked`, `test_wrong_story_id_prefix_blocked`, `test_task_count_not_incremented_by_guard`

### Step 8: Update dry run — `dry_runs/implement_dry_run.py`

Replace `task_created_payload()` with `task_create_pre_payload()` that builds PreToolUse TaskCreate shape with metadata.

Update the task-create phase section (lines 424-446):
- Replace `TaskCreated valid` → `TaskCreate PreToolUse with valid metadata → allow`
- Replace `TaskCreated invalid prefix` → `TaskCreate PreToolUse missing metadata → block`
- Add: `TaskCreate PreToolUse with unknown parent_task_id → block`
- Add: `TaskCompleted → subtask status updated to "completed"`

## Verification

1. Run tests: `pytest .claude/hooks/workflow/tests/test_task_guard.py -v`
2. Run full test suite: `pytest .claude/hooks/workflow/tests/ -v`
3. Run dry run: `python3 .claude/hooks/workflow/dry_runs/implement_dry_run.py --story-id SK-001`
4. Manual test: pipe TaskCreate PreToolUse JSON through guardrail CLI
