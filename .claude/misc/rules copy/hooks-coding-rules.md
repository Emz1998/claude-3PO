---
paths: .claude/hooks/**/*.py, scripts/claude_hooks/**/*.py
---

# Claude Hooks Coding Rules

## Architecture

**Two-layer design:**
- `.claude/hooks/dispatchers/` — thin entry-point scripts registered in `settings.local.json`
- `scripts/claude_hooks/` — Python package with all business logic

**Dispatchers** (~15 lines each) handle:
- `sys.path` bootstrap via `$CLAUDE_PROJECT_DIR`
- stdin JSON reading
- handler registry lookup
- per-handler error isolation (SystemExit re-raised, all others caught)

**Package structure:**
- `constants.py` — single source of truth: `PHASES`, `CODING_PHASES`
- `models.py` — pure Pydantic models (no I/O, no `sys.exit`, no `print`)
- `responses.py` — output functions: `block()`, `succeed()`, `set_decision()`, `build_output()`
- `state_store.py` — JSON state with file locking
- `file_manager.py` — low-level file I/O with `FileLock`
- `paths.py` — `ProjectPaths` dataclass (read-only properties)
- `context_injector.py` — markdown template rendering
- `handlers/` — all hook handlers (one `handle()` function per file)
- `sprint/` — standalone sprint domain (no hook imports)

## Handler Contract

Every handler module exposes exactly one function:
```python
def handle(hook_input: dict[str, Any]) -> None:
```

Handlers are registered in `handlers/__init__.py`:
```python
HANDLER_REGISTRY: dict[str, list[Handler]] = {
    "PreToolUse": [phase_guard.handle, log_guard.handle, commit_guard.handle],
    "PostToolUse": [session_recorder.handle, logging_reminder.handle, parallel_tasks.handle],
    "UserPromptSubmit": [build_entry.handle, implement_trigger.handle],
    "Stop": [stop_guard.handle],
}
```

## Import Rules

- Handlers import from `scripts.claude_hooks.models`, `scripts.claude_hooks.responses`, etc.
- Never import from `scripts.claude_hooks.utils` (deleted)
- Sprint modules import from `scripts.claude_hooks.file_manager`, `scripts.claude_hooks.state_store`, etc.
- Dispatchers use `sys.path` bootstrap — they are NOT importable modules

## Output Rules

- `block(reason)` — print to stderr, exit 2
- `succeed(context)` — print to stdout, exit 0
- `set_decision(**kwargs)` — JSON to stdout, exit 0
- `build_output(**kwargs)` — returns JSON string with camelCase keys
- JSON keys: `continue` (not `_continue`), `stopReason` (not `stop_reason`), `suppressOutput`, `hookSpecificOutput`

## Exit Codes

- `sys.exit(0)` — allow operation
- `sys.exit(2)` — block operation

## Naming

- All importable Python modules: `snake_case`
- Dispatcher scripts: `snake_case` (in `.claude/hooks/dispatchers/`)
- Constants: `UPPER_SNAKE_CASE`
- Handler functions: always named `handle`

## Testing

- Tests in `scripts/claude_hooks/tests/`
- Run: `python -m pytest scripts/claude_hooks/tests/ -v`
- Dispatcher tests invoke scripts as subprocesses (matching Claude Code runtime)
- Existing integration test: `scripts/claude_hooks/test/test.py`
