# Plan: Migrate State Schema to Nested Structure

## Context

The current workflow state is a flat dict with 20+ top-level keys. Many are related fields with inconsistent naming (`plan_file`, `plan_written`, `plan_review_iteration`, etc.). The user proposed a cleaner nested schema that groups related concerns and drops unused fields like `tasks_created`.

### Current → New Schema Mapping

```
OLD (flat)                          NEW (nested)
─────────────────────────────────   ─────────────────────────────────
workflow_active                     workflow_active
workflow_type                       workflow_type
phase                               phase
tdd                                 tdd
story_id                            story_id
skip_explore / skip_research        skip: ["explore"] | ["research"] | ["explore","research"] | []
instructions                        instructions
agents                              agents (unchanged)

plan_file                           plan.file_path
plan_written                        plan.written
plan_review_iteration               plan.review.iteration
plan_review_scores                  plan.review.scores
plan_review_status                  plan.review.status

tasks_created                       (REMOVED — unused)
tasks                               tasks (unchanged)

test_files_created                  tests.file_paths
test_review_result                  tests.review_result
test_run_executed                   tests.executed

plan_files_cache                    docs_to_read (populated from plan's "Files to Modify")
files_written                       files_written (keep — used by read_guard)
codebase_written                    codebase_written (keep — used by recorder)

validation_result                   validation_result
pr_status                           pr_status
ci_status                           ci_status
ci_check_executed                   (REMOVED — ci_status already tracks pass/fail/pending)
report_written                      report_written
last_reminder_phase                 last_reminder_phase (keep — internal to reminder.py)
```

## Approach

### 1. Update `skill_guard.py` — `_initial_state()`

Change the initial state dict to the new schema. Also update `_parse_skip_args()` to return a list.

```python
# Before
"skip_explore": True, "skip_research": False

# After  
"skip": ["explore"]
```

**File**: `guards/skill_guard.py:54-92`

### 2. Update `recorder.py` — all state writes

Every `state["plan_file"] = ...` becomes `state.setdefault("plan", {})["file_path"] = ...` etc.

Key changes:
- `record_write()`: `plan_file` → `plan.file_path`, `plan_written` → `plan.written`, `test_files_created` → `tests.file_paths`
- `record_bash()`: `test_run_executed` → `tests.executed`, remove `ci_check_executed` writes (rely on `ci_status`)
- `record_subagent_stop()`: `plan_review_scores` → `plan.review.scores`, `plan_review_status` → `plan.review.status`, `plan_review_iteration` → `plan.review.iteration`, `test_review_result` → `tests.review_result`
- `record_task_created()`: **DELETE** entirely (unused counter)
- `_dispatch()`: remove `TaskCreated` → `record_task_created` call

**File**: `recorder.py`

### 3. Update `guardrail.py` — `_handle_exit_plan_mode_pre()`

- `state.get("plan_written")` → `state.get("plan", {}).get("written")`
- `state.get("plan_review_status")` → `state.get("plan", {}).get("review", {}).get("status")`
- `state.get("plan_file")` → `state.get("plan", {}).get("file_path")`

**File**: `guardrail.py:70-117`

### 4. Update guards (reads only)

**`agent_guard.py`**:
- `state.get("skip_explore")` → `"explore" in state.get("skip", [])`
- `state.get("skip_research")` → `"research" in state.get("skip", [])`
- `state.get("plan_written")` → `state.get("plan", {}).get("written")`
- `state.get("test_files_created")` → `state.get("tests", {}).get("file_paths", [])`

**`read_guard.py`**:
- `state.get("plan_file")` → `state.get("plan", {}).get("file_path")`
- `state.get("plan_files_cache")` → `state.get("docs_to_read")`
- Write `plan_files_cache` → write `docs_to_read`

**`stop_guard.py`**:
- `state.get("test_run_executed")` → `state.get("tests", {}).get("executed")`
- `state.get("ci_check_executed")` → `state.get("ci_status") != "pending"` (field removed)

**File**: `guards/agent_guard.py`, `guards/read_guard.py`, `guards/stop_guard.py`

### 5. Update `reminder.py`

- `skip_explore` / `skip_research` → `"explore" in skip` / `"research" in skip`
- `plan_file` → `plan.file_path`
- `plan_files_cache` → `docs_to_read`
- `plan_review_iteration` → `plan.review.iteration`
- `plan_review_status` / `plan_review_scores` → `plan.review.status` / `plan.review.scores`
- `test_review_result` → `tests.review_result`

**File**: `reminder.py`

### 6. Update `auto_commit.py`

`get_story_context()` reads `state.get("tasks")` — unchanged. No action needed.

### 7. Update dry runs

Both dry run files use `make_state()` helpers that create the old flat schema. Update to new nested schema.

**Files**: `dry_runs/plan_dry_run.py`, `dry_runs/implement_dry_run.py`

### 8. Update tests

Every test file has a `make_state()` helper that builds the flat schema. Update all to nested schema. Also update assertions that check state fields directly.

**Files**: All `tests/test_*.py` files

## Files to Modify

| File | Change |
|------|--------|
| `guards/skill_guard.py` | New `_initial_state()` schema, `skip` as list |
| `recorder.py` | All state writes to nested paths, remove `record_task_created` |
| `guardrail.py` | Nested reads in `_handle_exit_plan_mode_pre` |
| `guards/agent_guard.py` | Nested reads for skip/plan/tests |
| `guards/read_guard.py` | `plan.file_path`, `docs_to_read` |
| `guards/stop_guard.py` | `tests.executed`, remove `ci_check_executed` |
| `reminder.py` | All nested reads |
| `dry_runs/plan_dry_run.py` | Updated payloads |
| `dry_runs/implement_dry_run.py` | Updated payloads |
| `tests/test_*.py` (all) | Updated `make_state()` helpers and assertions |

## Files NOT modified

`session_store.py`, `hook.py`, `logger.py`, `config/`, `guards/bash_guard.py`, `guards/write_guard.py`, `guards/webfetch_guard.py`, `guards/subagent_stop_guard.py`, `guards/task_guard.py`, `auto_commit.py`, dispatchers (they don't read state fields directly)

## Verification

1. `pytest .claude/hooks/workflow/tests/` — all 361 tests pass
2. `python3 .claude/hooks/workflow/dry_runs/plan_dry_run.py --skip-all` — full pass
3. `python3 .claude/hooks/workflow/dry_runs/implement_dry_run.py` — full pass
4. Inspect `state.jsonl` after `/implement` — verify nested structure
