# Plan: Migrate state.json → state.jsonl (Session-Scoped State)

## Context

The workflow hooks system uses a single `state.json` shared by all Claude sessions. This causes two problems:
1. **Only one workflow can run at a time** — overlapping sessions corrupt each other's state
2. **Headless sessions (auto_commit) are blocked by guards** — the headless Claude has a different `session_id` but guards read the main session's phase from shared `state.json`, blocking reads/writes that should be allowed

Replace with `state.jsonl` where each line is one session's state, keyed by `session_id` (UUID from hook stdin). Each session's guards only see their own state — headless sessions with `workflow_active=false` pass through all guards freely.

## Approach

### 1. Rewrite `session_state.py` → `session_store.py`

**Rename + rewrite**: `.claude/hooks/workflow/session_state.py` → `session_store.py`

The current `session_state.py` is full of dead code (typed properties, setters, helpers that nothing uses). Replace it entirely with a clean `SessionStore` class that:

- Backs state in a JSONL file (one JSON line per session, keyed by `session_id`)
- Same public API as `StateStore`: `load()`, `save()`, `update()`, `get()`, `set()`, `reset()`, `reinitialize()`, `delete()`
- Constructor: `__init__(self, session_id: str, jsonl_path: Path = DEFAULT_STATE_JSONL_PATH)`
- Uses `FileLock` on `state.jsonl.lock` (same pattern as `StateStore`)
- Every operation: acquire lock → read all lines → parse into `dict[session_id, state_dict]` → operate on target session → rewrite file → release lock
- `cleanup_inactive()` class method: remove lines where `workflow_active == False`

### 2. Update `config/paths.py`

Add `DEFAULT_STATE_JSONL_PATH = WORKFLOW_ROOT / "state.jsonl"`.

### 3. Update `guardrail.py`

In `_dispatch()` (line 157):
- Extract `session_id = hook_input.get("session_id", "default")`
- Replace `StateStore(state_path)` → `SessionStore(session_id)`
- Update `_state_path()` / env var handling for JSONL path

### 4. Update `recorder.py`

Same as guardrail in `_dispatch()` (line 466):
- Extract `session_id`, use `SessionStore(session_id)`

### 5. Update all 6 dispatchers

Each creates `StateStore(DEFAULT_STATE_PATH)` inline → `SessionStore(session_id)` where `session_id = raw_input["session_id"]`.

- `dispatchers/pre_tool_use.py` — line 75
- `dispatchers/post_tool_use.py` — inline store creation
- `dispatchers/session_start.py` — line 25 (also add `SessionStore.cleanup_inactive()` call)
- `dispatchers/subagent_start.py` — line 20
- `dispatchers/subagent_stop.py` — line 54
- `dispatchers/user_prompt_submit.py` — line 48

### 6. Update `auto_commit.py`

`get_story_context()` reads `DEFAULT_STATE_PATH` directly → use `SessionStore(session_id)` with session_id from `raw_input`.

### 7. Strip `build_entry.py` of workflow activation

Remove `activate_workflow()` and the `state_store` import. The `/implement` skill (via `skill_guard.py`) handles activation. `BuildEntry` only discovers prompts and launches parallel sessions.

### 8. Update `skill_guard.py` import

Change `from workflow.state_store import StateStore` → `from workflow.session_store import SessionStore`. The `store` parameter it receives will already be a `SessionStore` from guardrail.

### 9. Update dry runs

Both `dry_runs/plan_dry_run.py` and `dry_runs/implement_dry_run.py` directly reference `STATE_PATH = ... / "state.json"` and manipulate it with raw `json.loads`/`json.dumps`. They also pass it via env vars to guardrail/recorder subprocesses.

Changes needed:
- `STATE_PATH` → `STATE_JSONL_PATH = ... / "state.jsonl"`
- Backup/restore logic: read/write JSONL instead of JSON
- Final state inspection: use `SessionStore("s").load()` instead of `json.loads(STATE_PATH.read_text())`
- The `session_id: "s"` in all payloads already exists — this becomes the JSONL key
- The env var override (`GUARDRAIL_STATE_PATH`/`RECORDER_STATE_PATH`) should point to temp JSONL path

### 10. Update tests

- **Rewrite**: `tests/test_state_store.py` → test `SessionStore` with JSONL: multi-session isolation, concurrent access, cleanup
- **Update**: `tests/conftest.py` — fixtures use `SessionStore`
- **Update**: Guard/recorder test files — use `SessionStore(session_id, tmp_jsonl)` instead of `StateStore(tmp_json)`

### 11. Clean up

- Delete `session_state.py` (replaced by `session_store.py`)
- Delete `state.json` and `state.lock`
- Update all imports from `session_state` → `session_store`

## Files to Modify

| File | Change |
|------|--------|
| `session_store.py` | **NEW** (replaces `session_state.py`) — JSONL session store |
| `session_state.py` | **DELETE** |
| `config/paths.py` | Add `DEFAULT_STATE_JSONL_PATH` |
| `guardrail.py` | Use `SessionStore` in `_dispatch()` |
| `recorder.py` | Use `SessionStore` in `_dispatch()` |
| `dispatchers/pre_tool_use.py` | Use `SessionStore` |
| `dispatchers/post_tool_use.py` | Use `SessionStore` |
| `dispatchers/session_start.py` | Use `SessionStore` + cleanup |
| `dispatchers/subagent_start.py` | Use `SessionStore` |
| `dispatchers/subagent_stop.py` | Use `SessionStore` |
| `dispatchers/user_prompt_submit.py` | Use `SessionStore` |
| `auto_commit.py` | Use `SessionStore` |
| `lib/build_entry.py` | Remove workflow activation |
| `guards/skill_guard.py` | Update import |
| `tests/conftest.py` | Update fixtures |
| `tests/test_state_store.py` | Rewrite for `SessionStore` |
| Guard/recorder test files | Update store creation |
| `dry_runs/plan_dry_run.py` | STATE_PATH → JSONL, backup/restore, final state read |
| `dry_runs/implement_dry_run.py` | STATE_PATH → JSONL, backup/restore, final state read |

## Files NOT modified (same API)

All 9 guards (except `skill_guard.py` import), `reminder.py`, `hook.py`, `logger.py`, `state_store.py`, `lib/file_manager.py`

## Verification

1. `pytest .claude/hooks/workflow/tests/` — all tests pass with new JSONL store
2. Manual: run `/implement`, check `state.jsonl` has one line with correct session_id
3. Cleanup: complete workflow → new session → old inactive line removed
