# Plan: Separate Recording Logic from Guardrail Logic

## Context

The guards in `.claude/hooks/workflow/guards/` currently mix two concerns:
1. **Guardrail logic** — deciding whether to allow/block an action (PreToolUse validation)
2. **Recording logic** — tracking what Claude has done by updating state (PostToolUse side-effects, agent tracking, phase advancement)

This refactoring extracts all recording logic into a new `recorder.py` module, making each guard responsible only for validation (allow/block decisions), while `recorder.py` owns all state mutations that track what happened.

## Approach

Create `recorder.py` at `.claude/hooks/workflow/recorder.py` with all recording functions. Update guards to delegate recording calls to it. Update `guardrail.py` dispatch to route PostToolUse events directly to recorder instead of through guards.

### What moves to `recorder.py`

| Source | Logic | Destination function |
|---|---|---|
| `agent_guard._record_agent()` | Append agent to `agents[]` | `record_agent()` |
| `agent_guard.validate()` L139-141 | Phase advance write-code→validate | `record_agent_phase_advance()` |
| `write_guard.handle_post()` L138-145 | Track `files_written[]` | `record_write()` (composite) |
| `write_guard.handle_post()` L148-155 | Plan file + phase→review | `record_write()` |
| `write_guard.handle_post()` L159-167 | Track `test_files_created[]` | `record_write()` |
| `write_guard.handle_post()` L170-184 | CI-check regression | `record_write()` |
| `write_guard.handle_post()` L187-194 | Report + phase→completed | `record_write()` |
| `bash_guard.handle_post()` L68-69 | `test_run_executed` | `record_bash()` (composite) |
| `bash_guard.handle_post()` L73-78 | PR created + phase→ci-check | `record_bash()` |
| `bash_guard.handle_post()` L81-91 | CI check tracking | `record_bash()` |
| `review_guard.handle()` entire | Mark agent completed, parse scores, advance phases | `record_subagent_stop()` |
| `task_guard.validate()` L44-46 | Increment `tasks_created` | `record_task_created()` |
| `guardrail._handle_exit_plan_mode_post()` | Phase advance after ExitPlanMode | `record_exit_plan_mode()` |

### What stays in each guard

- **agent_guard.py**: `validate()` — phase/type/count checks only. Calls `recorder.record_agent()` on allow
- **write_guard.py**: `validate_pre()` + all `_is_*` helper functions (unchanged). `handle_post()` removed
- **bash_guard.py**: `validate_pre()` + command classification helpers (unchanged). `handle_post()` removed
- **review_guard.py**: Reduced to thin delegation → `recorder.record_subagent_stop()` (or deleted, with guardrail.py calling recorder directly)
- **task_guard.py**: `validate()` still validates prefix, calls `recorder.record_task_created()` on allow
- **Other guards**: `read_guard`, `skill_guard`, `stop_guard`, `webfetch_guard` — unchanged

## Steps

### Step 1: Create `recorder.py`

New file at `.claude/hooks/workflow/recorder.py` with:
- `record_agent(store, agent_type, tool_use_id)` — from `agent_guard._record_agent()`
- `record_agent_phase_advance(store)` — from `agent_guard.validate()` L139-141
- `record_write(hook_input, store)` — composite replacing `write_guard.handle_post()`. Imports `is_plan_file`, `is_test_file`, `is_code_file`, `is_report_file`, `get_file_path` from write_guard
- `record_bash(hook_input, store)` — composite replacing `bash_guard.handle_post()`. Imports `is_pr_command`, `is_test_run`, `is_ci_check` from bash_guard
- `record_task_created(store)` — from `task_guard.validate()` L44-46
- `record_subagent_stop(hook_input, store)` — entire `review_guard.handle()` logic including `parse_scores`, `_mark_first_running_completed`, `_required_explore_agents`, `_count_completed`, and `PLAN_REVIEW_THRESHOLD/MAX` constants
- `record_exit_plan_mode(hook_input, store)` — from `guardrail._handle_exit_plan_mode_post()`

### Step 2: Expose helper functions in write_guard and bash_guard

- `write_guard.py`: Rename `_is_plan_file` → `is_plan_file`, `_is_test_file` → `is_test_file`, etc. (drop underscore prefix). Remove `handle_post()` and legacy `validate()` shim
- `bash_guard.py`: Rename `_is_pr_command` → `is_pr_command`, etc. Remove `handle_post()` and legacy `validate()` shim

### Step 3: Update agent_guard.py

- Remove `_record_agent()` function
- Replace calls with `recorder.record_agent(store, agent_type, tool_use_id)`
- Replace L139-141 phase advance with `recorder.record_agent_phase_advance(store)`

### Step 4: Update task_guard.py

- Replace inline `_increment` / `store.update(_increment)` with `recorder.record_task_created(store)`

### Step 5: Delete review_guard.py

- Delete `.claude/hooks/workflow/guards/review_guard.py` entirely
- All logic (parse_scores, helpers, handle) moves to `recorder.py`
- `guardrail.py` routes `SubagentStop` directly to `recorder.record_subagent_stop()`

### Step 6: Update guardrail.py dispatch

```python
from workflow import recorder

# PostToolUse routing changes:
if tool in ("Write", "Edit"):
    return recorder.record_write(hook_input, store)  # was write_guard.handle_post
if tool == "Bash":
    return recorder.record_bash(hook_input, store)    # was bash_guard.handle_post
if tool == "ExitPlanMode":
    return recorder.record_exit_plan_mode(hook_input, store)  # was _handle_exit_plan_mode_post

# SubagentStop routing change:
if event == "SubagentStop":
    return recorder.record_subagent_stop(hook_input, store)  # was review_guard.handle
```

Remove `_handle_exit_plan_mode_post()` from guardrail.py. Remove `review_guard` from imports (file deleted).

### Step 7: Update tests

- `test_write_guard.py`: Tests calling `write_guard.handle_post()` → change to `recorder.record_write()`
- `test_bash_guard.py`: Tests calling `bash_guard.handle_post()` → change to `recorder.record_bash()`
- `test_review_guard.py`: Tests calling `review_guard.handle()` → change to `recorder.record_subagent_stop()`
- Create `test_recorder.py` if preferred (or just update import paths in existing tests)

### Step 8: Make recorder.py executable + validate

- `chmod +x recorder.py`
- Run full test suite: `pytest .claude/hooks/workflow/tests/`

## Files to Modify

| File | Action |
|---|---|
| `.claude/hooks/workflow/recorder.py` | **CREATE** — all recording functions |
| `.claude/hooks/workflow/guardrail.py` | Edit — update PostToolUse/SubagentStop dispatch, remove `_handle_exit_plan_mode_post` |
| `.claude/hooks/workflow/guards/write_guard.py` | Edit — remove `handle_post()`, expose helpers (drop underscore) |
| `.claude/hooks/workflow/guards/bash_guard.py` | Edit — remove `handle_post()`, expose helpers (drop underscore) |
| `.claude/hooks/workflow/guards/agent_guard.py` | Edit — remove `_record_agent`, delegate to recorder |
| `.claude/hooks/workflow/guards/review_guard.py` | **DELETE** — all logic moves to recorder |
| `.claude/hooks/workflow/guards/task_guard.py` | Edit — delegate recording to recorder |
| `.claude/hooks/workflow/tests/test_write_guard.py` | Edit — update handle_post calls to recorder |
| `.claude/hooks/workflow/tests/test_bash_guard.py` | Edit — update handle_post calls to recorder |
| `.claude/hooks/workflow/tests/test_review_guard.py` | **RENAME** to `test_recorder.py` — update imports to recorder |

## Verification

1. Run `pytest .claude/hooks/workflow/tests/ -v` — all existing tests must pass
2. Run dry runs: `python3 .claude/hooks/workflow/dry_runs/implement_dry_run.py` and `plan_dry_run.py`
3. Verify no circular imports: `python3 -c "from workflow import recorder"`
4. Verify guards only contain validation logic (no `store.update`/`store.set` calls except through recorder)
