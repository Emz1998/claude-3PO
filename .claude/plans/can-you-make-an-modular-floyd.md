# Plan: state.jsonl → single state.json + single-session StateStore + auto_resolver.py

## Context

Three coupled changes, done in order:

1. **Migrate persistence format** — `state.jsonl` (multi-session JSONL) → **one `state.json` file** at `.claude/state.json` (resolved to `claude-3PO/scripts/state.json` by call sites). Flat JSON object, one session only.
2. **Make `StateStore` single-session** — drop all multi-session machinery: no `session_id` filtering, no cross-session iteration, no list scan. One `StateStore` instance owns the one `state.json` file. `--reset` / `--takeover` in `initializer.py` operate on that single file.
3. **Build `auto_resolver.py`** — long-running script that watches `state.json` and calls `resolver.resolve(config, state)` on every modification. Wraps the existing `resolve(config, state)` at `resolver.py:686-698`. Target: the empty `claude-3PO/scripts/utils/auto_resolver.py` (cleared in commit `c942ea8`).

Why now: `resolver.py` already has the clean entry point; today it only runs inside synchronous hooks. A watcher closes the loop so state drift triggers auto-advance without waiting for the next hook. Going single-session simplifies the store (no filtering/indexing), the config (one path), and the watcher (one file, no dispatch).

## Design decisions

- **File:** one `state.json` holding the session dict directly (not wrapped by session_id). Lives at the path configured by `paths.state_json` (default `".claude/state.json"`).
- **StateStore constructor:** `StateStore(state_path: Path, default_state=None)`. No `session_id` parameter. The `session_id` value is still recorded **inside** the state dict (for hook traceability / log correlation) but the store does not filter or index on it.
- **Dropped behaviors (explicit):**
  - `find_active_by_story` — **deleted**. Duplicate-story guard in `initializer.py:215-222` is removed entirely. The user accepted this.
  - `cleanup_inactive` — **deleted**. The `initializer.py:200` call is removed. With one file, nothing accumulates.
  - `deactivate_by_story` — **deleted**. Replaced by the single-file behavior below.
  - `_find_session`, `_read_all_lines`, `_write_all_lines` — **deleted** (no more list scan / JSONL format).
- **`--reset` (single-file):** overwrite `state.json` with a freshly-built initial state.
- **`--takeover` (single-file):** if `state.json` exists, leave it in place (do not reinitialize). If not, fall through to normal init.
- **Lock model:** keep `filelock` on a sibling `state.json.lock`. Only one lock, no contention.
- **Config key rename:** `paths.state_jsonl` → `paths.state_json` in `config/config.json` (value `".claude/state.json"`). Rename `Config.default_state_jsonl` → `Config.default_state_json`.
- **Watcher library:** `watchdog` (pure-Python). The user originally said watchman; watchdog is chosen to avoid the `pywatchman` + watchman-binary dependency. Easy to swap later.
- **auto_resolver entry point:** standalone CLI at `claude-3PO/scripts/utils/auto_resolver.py` with `if __name__ == "__main__": main()`. Not a dispatcher (no stdin hook), so `utils/` is correct per `CLAUDE.md`.
- **auto_resolver handler:** `AutoResolverHandler(FileSystemEventHandler)` — `on_modified` for `state.json` constructs `StateStore(state_path)` + `Config()`, calls `resolver.resolve(config, state)`, logs a one-line summary. No filename parsing, no session_id extraction.
- **TDD:** write/revise tests first. Deleted-method suites in `test_state_store.py` go away; remaining suites are updated for the new constructor and file layout; new `test_auto_resolver.py` is written first.
- **One-time data migration:** existing `state.jsonl` has 1 line → write its single dict to `state.json`. Small one-shot `scripts/utils/migrate_state.py`; delete after use.

## Files changed

### Phase 1 — single-session StateStore + format migration

- `claude-3PO/scripts/lib/state_store/base.py`:
  - Delete `_read_all_lines`, `_write_all_lines`, `_find_session`, `_is_active_for_story`.
  - Replace with `_read()` (read+parse the single JSON file; return `default_state` if missing/empty) and `_write(data)` (serialize the single dict).
  - Rewrite `load`, `save`, `update` against the single file.
  - Delete `find_active_by_story`, `deactivate_by_story`, `cleanup_inactive`.
  - Change constructor: `StateStore(state_path, default_state=None)`. Remove `session_id` parameter and the `session_id` property (sessions no longer scope the store).
- `claude-3PO/scripts/config/config.json:201` — `"state_jsonl": ".claude/state.jsonl"` → `"state_json": ".claude/state.json"`.
- `claude-3PO/scripts/config/config.py:488-495` — rename property `default_state_jsonl` → `default_state_json`.
- `claude-3PO/scripts/utils/initializer.py`:
  - Line 24 — `STATE_PATH = SCRIPTS_DIR / "state.jsonl"` → `STATE_PATH = SCRIPTS_DIR / "state.json"`.
  - Line 199 — `StateStore(state_path, session_id=session_id)` → `StateStore(state_path)`; keep writing `session_id` *inside* the state dict via `build_initial_state`.
  - Line 200 — drop `store.cleanup_inactive()`.
  - Lines 214-232 — delete the duplicate-story guard block. Rewrite:
    - `--reset`: always call `store.reinitialize(build_initial_state(...))`.
    - `--takeover`: if `state_path.exists()` and has non-empty content, return without reinitializing; otherwise reinitialize.
- **Dispatcher / util call sites** (all drop the `session_id` kwarg to `StateStore`, all swap `"state.jsonl"` → `"state.json"`):
  - `utils/summarize_prompt.py:27`
  - `dispatchers/pre_tool_use.py:50`, `post_tool_use.py:60`, `subagent_start.py:44`, `stop.py:46`, `task_completed.py:31`
  - `dispatchers/task_created.py:33-36`, `subagent_stop.py:44-46` — rename env var to match new filename if desired (cosmetic).
- `tests/conftest.py:62-66` — fixture writes a single JSON dict to `state.json` instead of a JSONL line.
- `tests/test_state_store.py` — delete the `cleanup_inactive` suite (lines 382-429) and any `find_active_by_story` / `deactivate_by_story` / session-isolation tests; update remaining tests for the new constructor.
- `tests/test_base_state.py`, `test_build_state.py`, `test_implement_state.py`, `test_specs_state.py` — update constructor calls (`StateStore(path, "sid")` → `StateStore(path)`); drop multi-session assertions.
- `claude-3PO/scripts/utils/migrate_state.py` (new, one-shot) — read any existing `state.jsonl`'s single line, write it as `state.json`, print summary. Delete after successful migration.

### Phase 2 — auto_resolver

- `claude-3PO/scripts/utils/auto_resolver.py` (currently empty):
  - `main()`: parse `--state-path` (default `Config().default_state_json`), start the observer on the parent directory filtered to the state filename, block on SIGINT.
  - `AutoResolverHandler(FileSystemEventHandler)`: `on_modified` checks the changed path equals the configured `state.json`, constructs `StateStore(state_path)` + `Config()`, calls `resolver.resolve(config, state)`, logs a one-line summary.
  - `AutoResolver`: thin glue (observer setup, handler wiring, shutdown).
  - Every method ≤15 lines per project style. Google-style docstrings with Args/Returns/Raises/SideEffect/Example.
- `tests/test_auto_resolver.py` (new, TDD-first): mock `resolver.resolve`, touch `state.json` in a tmp dir, assert `resolve` was called once with a `StateStore` bound to the correct path.

## Reuse (don't re-implement)

- `resolver.resolve(config, state)` at `resolver.py:686-698` — the entry point auto_resolver calls; do not duplicate.
- `FileLock` pattern at `base.py:85` — reuse for the single `state.json.lock`.
- `Config().default_state_json` — auto_resolver reads it for its default path.
- `StateStore` public API (`load`, `save`, `update`, `get`, slice accessors) — signatures unchanged; every caller keeps working after the constructor rename.

## Verification

1. **Unit tests:** `pytest claude-3PO/scripts/tests/test_state_store.py claude-3PO/scripts/tests/test_base_state.py claude-3PO/scripts/tests/test_build_state.py claude-3PO/scripts/tests/test_implement_state.py claude-3PO/scripts/tests/test_specs_state.py` — all pass.
2. **Initializer tests:** `pytest claude-3PO/scripts/tests/test_initializer.py` (if present) — `--reset` rewrites, `--takeover` preserves, no duplicate-story guard.
3. **Auto-resolver tests:** `pytest claude-3PO/scripts/tests/test_auto_resolver.py` — watcher fires `resolve` on modification.
4. **Manual smoke:**
   - `python claude-3PO/scripts/utils/migrate_state.py` once; verify `state.json` appears.
   - Run `python claude-3PO/scripts/utils/auto_resolver.py` in one terminal.
   - In another terminal, mutate `state.json` (e.g. `StateStore(path).update(lambda s: s.__setitem__("phase", "plan"))`).
   - Confirm the auto_resolver log shows `resolve` fired.
5. **Hook regression:** stdin-feed `post_tool_use.py` and confirm it still loads/saves state against the single-file store.

## Out of scope

- Switching to `pywatchman` — noted as a future option.
- Deleting the old `state.jsonl` file — leave one release as rollback; remove in a follow-up commit.
- Multi-concurrent-session support — explicitly dropped by this plan.
- Running auto_resolver under a process manager — foreground-only for now.
