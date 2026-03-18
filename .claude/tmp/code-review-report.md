---
confidence_score: 82
quality_score: 45
---

# Code Review Report -- Avaris AI Workflow Hooks System

**Reviewer:** Code Review Specialist (Subagent)
**Date:** 2026-03-16
**Scope:** `.claude/hooks/workflow/` and `github_project/project_manager.py`
**Branch:** refactor/claude-config

---

## Summary

The codebase implements a workflow hooks system for Claude Code sessions, enforcing phase ordering, tool blocking, review loops, and state management. While the overall architecture is reasonable, the review identified several **critical bugs**, **security concerns**, and **significant quality issues** that need attention before this branch can be considered production-ready.

---

## Critical Findings

### C-1: Infinite Recursion in `SessionState.delete()` (Bug)

**File:** `/home/emhar/avaris-ai/.claude/hooks/workflow/session_state.py`, line 37

```python
def delete(self) -> None:
    self.delete()
```

This method calls itself unconditionally, causing a `RecursionError` (stack overflow) whenever `delete()` is invoked. It should call `super().delete()` to delegate to the parent `StateStore.delete()` method.

**Severity:** Critical

---

### C-2: `set_phase` and `set_agent` Silently Fail When Keys Are Missing (Bug)

**File:** `/home/emhar/avaris-ai/.claude/hooks/workflow/session_state.py`, lines 27-28, 58-59

```python
def set_phase(self, query, value):
    self.update(lambda d: d.get("phase", {}).update({query: value}))
```

If `d` does not contain the key `"phase"`, `d.get("phase", {})` returns a **new temporary dict** which is immediately updated and discarded. The state file is never actually modified. The same issue exists in `set_agent` (line 59) and in `PhaseGuard.run()` (`phase_guard.py`, line 57).

**Severity:** Critical -- state mutations are silently lost.

---

### C-3: Undefined Variable `story_id` in `CleanupTrigger.run()` (Bug)

**File:** `/home/emhar/avaris-ai/.claude/hooks/workflow/handlers/cleanup_trigger.py`, line 48

```python
remove_worktree(story_id)
```

The variable `story_id` is never defined in this scope. This will raise a `NameError` at runtime. It should likely be `self._session.get("story_id")`.

**Severity:** Critical -- runtime crash.

---

### C-4: Missing Import -- `cfg` Not Imported in `cleanup_trigger.py` (Bug)

**File:** `/home/emhar/avaris-ai/.claude/hooks/workflow/handlers/cleanup_trigger.py`, line 32

```python
self._session = SessionState(Path(cfg("paths.workflow_state")))
```

The `cfg` function is used but never imported. This will raise a `NameError` when `CleanupTrigger` is instantiated.

**Severity:** Critical -- runtime crash.

---

### C-5: `set_story_id.py` References Wrong Argument Name (Bug)

**File:** `/home/emhar/avaris-ai/.claude/hooks/workflow/utils/set_story_id.py`, line 15

```python
parser.add_argument("--story-id", type=str, required=True)
args = parser.parse_args()
session_id = args.session_id  # AttributeError: 'story_id' was defined, not 'session_id'
```

The argument is defined as `--story-id` (accessible as `args.story_id`), but the code reads `args.session_id`, which does not exist. This will raise an `AttributeError` every time the script runs.

**Severity:** Critical -- runtime crash.

---

## High Findings

### H-1: Missing `main()` Guard in `commit_ensurer.py` (Bug)

**File:** `/home/emhar/avaris-ai/.claude/hooks/workflow/guards/commit_ensurer.py`

The file has no `if __name__ == "__main__": main()` guard at the bottom. The `main()` function is defined but never called as a script entry point. If this file is intended to be invoked as a hook, it will run and exit without doing anything.

**Severity:** High

---

### H-2: `normalize_tool_for_block` Crashes on `Read` Tool (Bug)

**File:** `/home/emhar/avaris-ai/.claude/hooks/workflow/utils/normalize_tool.py`, lines 11-25

The match statement handles `skill`, `agent`, `write|edit`, and `bash`, but `read`, `enterplanmode`, and `exitplanmode` all fall through to the default case which raises `ValueError`. Since `Read` is a valid tool in `ToolName`, any hook using `normalize_tool_for_block` on a Read event will crash.

**Severity:** High -- crashes on valid tool usage.

---

### H-3: `review_loop.py` Falls Through After `Hook.success_response()` (Bug)

**File:** `/home/emhar/avaris-ai/.claude/hooks/workflow/review/review_loop.py`, lines 98-114

```python
if not need_iteration:
    ...
    Hook.success_response(message)  # calls sys.exit(0)

iteration_left = review_state.get("iteration_left", MAX_ITERATIONS)
iteration_left -= 1
```

While `Hook.success_response` calls `sys.exit(0)` so the fall-through code won't actually execute, this is fragile and misleading. The logic should use `return` or `else` to make the intent clear. If `sys.exit` were ever removed or mocked in tests, the iteration count would be incorrectly decremented.

**Severity:** High -- fragile control flow.

---

### H-4: `review_loop.py` Sets `fully_blocked.exception` as a Dict, Not a List (Bug)

**File:** `/home/emhar/avaris-ai/.claude/hooks/workflow/review/review_loop.py`, lines 116-123

```python
session.set("fully_blocked", {
    "status": "active",
    "reason": message,
    "exception": {"skill": "refactor"},  # dict, not list of lists
})
```

The `fully_blocked` guard (`fully_blocked.py`) expects `exception` to be a `list[list[str]]` (e.g., `[["skill", "refactor"]]`). Passing a dict will cause `is_tool_in_exceptions` to iterate over dict keys rather than pairs, leading to incorrect blocking behavior.

The same issue exists in `commit_ensurer.py` line 18 and `refactor.py` line 33 (uses `"exceptions"` instead of `"exception"`).

**Severity:** High -- blocking logic silently breaks.

---

### H-5: `refactor.py` Uses Wrong Key Name `"exceptions"` (Bug)

**File:** `/home/emhar/avaris-ai/.claude/hooks/workflow/review/refactor.py`, line 33

```python
"exceptions": {"skill": "refactor"},
```

The key should be `"exception"` (singular) to match what `fully_blocked.py` reads via `session.fully_blocked("exception")`. With the wrong key, the exception list will never be found and all tools will be blocked.

**Severity:** High

---

### H-6: `release_force_stop` Sets Inconsistent State Shape (Bug)

**File:** `/home/emhar/avaris-ai/.claude/hooks/workflow/state_handlers/release_force_stop.py`, line 14

```python
session.set("force_stop", False)
```

The default state defines `force_stop` as a dict `{"reason": None, "status": "inactive"}`. Setting it to `False` changes the type, which will break `force_stop.py` line 17 where it calls `.get("status", "inactive")` on the value. Accessing `.get()` on a boolean raises `AttributeError`.

**Severity:** High

---

### H-7: `set_review_by_key` and `set_review` Default to Empty String (Bug)

**File:** `/home/emhar/avaris-ai/.claude/hooks/workflow/session_state.py`, lines 49, 54

```python
review_data = self.get("review", "")
new_review_data = {**review_data, key: val}
```

If the `review` key is missing, `self.get("review", "")` returns an empty string `""`. Then `{**"", key: val}` will raise `TypeError: cannot unpack non-mapping str`. The default should be `{}`.

**Severity:** High

---

## Medium Findings

### M-1: Hardcoded Absolute Paths Throughout Codebase (Security/Portability)

**Files:** Multiple locations including:
- `config.yaml` lines 4-6: `/home/emhar/avaris-ai/.claude/hooks/workflow/...`
- `reviewer_recorder.py` line 34: `/home/emhar/avaris-ai/.claude/tmp/`
- `report_ensurer.py` line 28: `/home/emhar/avaris-ai/.claude/tmp/`
- `parallel_session.py` line 5: `~/avaris-ai/...`

All paths are hardcoded to a specific user's home directory, making the project non-portable and potentially exposing the user's directory structure.

**Severity:** Medium

---

### M-2: Pervasive `sys.path.insert(0, ...)` Manipulation (Quality)

Nearly every file in the workflow system manipulates `sys.path` with varying parent-resolution depths. Some use `sys.path.insert(0, ...)`, others use `sys.path.append(...)`. This is fragile and error-prone. A proper package installation (e.g., `pip install -e .` with a `pyproject.toml`) would eliminate this entirely.

**Severity:** Medium

---

### M-3: Module-Level State Store Instantiation (Quality/Performance)

**Files:**
- `workflow_gate.py` line 21: `state_store = StateStore(PATH, ...)`
- `state_handlers/recorder.py` line 17: `SESSION = SessionState(...)`
- `state_handlers/reviewer_recorder.py` line 16: `SESSION = SessionState(...)`

Creating `StateStore`/`SessionState` at module import time means the state file is touched (and potentially created) every time any module in the workflow package is imported, even if that particular handler is not being invoked.

**Severity:** Medium

---

### M-4: `StateStore.get()` Has Surprising Write-on-Read Side Effect (Quality)

**File:** `/home/emhar/avaris-ai/.claude/hooks/workflow/state_store.py`, lines 29-34

```python
def get(self, key: str, default: Any = None) -> Any:
    data = self.load()
    if key not in data and default is not None:
        self.set(key, default)
        return default
    return data.get(key, default)
```

A `get()` method should not write to the store. This violates the principle of least surprise and causes unnecessary file I/O and locking on every read when a default is provided.

**Severity:** Medium

---

### M-5: `config.get()` Returns `None` for Falsy Values (Bug)

**File:** `/home/emhar/avaris-ai/.claude/hooks/workflow/config.py`, line 42

```python
data = data.get(key)
if data is None:
    return default
```

This conflates an explicitly-set `None` value in config with a missing key. If a config key is set to `None`, `0`, `False`, or `""`, the function behaves differently for `None` vs the others. Only `None` triggers the default, which is fine for this use case, but a value explicitly set to `None` in YAML would be indistinguishable from a missing key.

**Severity:** Low

---

### M-6: `FileManager.delete_dir` Fails on Non-Empty Directories (Quality)

**File:** `/home/emhar/avaris-ai/.claude/hooks/workflow/lib/file_manager.py`, line 167

```python
def delete_dir(path: Path) -> None:
    path.rmdir()
```

`Path.rmdir()` only works on empty directories. If a directory contains any files, this raises `OSError`. Should use `shutil.rmtree()` if the intent is to remove a directory tree.

**Severity:** Medium

---

### M-7: `workflow_gate.py` Creates Two StateStore Instances for the Same Path (Quality)

**File:** `/home/emhar/avaris-ai/.claude/hooks/workflow/workflow_gate.py`

Line 21 creates a module-level `state_store`, and line 44 creates a new `StateStore(PATH)` inside `check_workflow_gate()`. This is redundant and could lead to subtle caching inconsistencies.

**Severity:** Low

---

### M-8: `stop_guard.py` Blocks When Workflow Is Inactive (Logic Issue)

**File:** `/home/emhar/avaris-ai/.claude/hooks/workflow/guards/stop_guard.py`, line 57

```python
if not is_workflow_active:
    Hook.block("Workflow is not active.")
```

This blocks the stop action when the workflow is inactive, which seems backwards. If the workflow is not active, the stop should likely be allowed (not blocked). Every other guard in the codebase returns early when the workflow is inactive.

**Severity:** Medium

---

## Low Findings

### L-1: `config.yaml` Has Trailing Empty List Item (Quality)

**File:** `/home/emhar/avaris-ai/.claude/hooks/workflow/config.yaml`, line 68

```yaml
commands:
  - "commit": "git commit"
  - "push": "git push"
  -
```

The trailing `-` creates a `None` entry in the list, which could cause issues if the list is iterated.

**Severity:** Low

---

### L-2: Debug `print()` Statements in Production Guards (Quality)

**Files:** `phase_guard.py` (lines 40, 49), `pre_coding_phase.py` (lines 44, 48, 51), `code_phase.py` (line 34), multiple others.

Multiple guards contain `print()` statements that appear to be debug output rather than intentional logging. These should use the existing `workflow_log.log()` function or be removed.

**Severity:** Low

---

### L-3: Duplicate `validate_hook_input` Functions (DRY Violation)

**Files:** `guards/tool_block.py` lines 19-33, `guards/fully_blocked.py` lines 19-33

These two files contain identical `validate_hook_input` functions. This should be extracted to a shared utility.

**Severity:** Low

---

### L-4: Docstrings Copied Incorrectly Between Files (Quality)

**Files:**
- `fully_blocked.py` line 1: `"""PostToolUse handler -- injects /simplify system message..."`
- `tool_block.py` line 1: `"""PostToolUse handler -- injects /simplify system message..."`
- `report_ensurer.py` line 1: `"""Decision guard -- blocks stop if /decision was not invoked."`

Several files have docstrings copied from other files that do not describe their actual purpose.

**Severity:** Low

---

### L-5: Unused Imports (Quality)

**Files:**
- `hook.py` lines 2-8: `Generic`, `TypeVar`, `get_args`, `get_origin`, `Self`, `ClassVar`, `dataclass` are all imported but unused.
- `pre_coding_phase.py` line 11: `PostToolUseInput` and `StopInput` imported but unused.
- `context_injector.py` line 8: `Path` imported twice.

**Severity:** Low

---

## Architecture Notes

1. **State consistency:** The system has no transactional guarantees across multiple `set()` calls. A crash between two successive `set()` calls in `recorder.py` or `review_loop.py` could leave state in an inconsistent state. The file-locking in `FileManager` protects individual operations but not multi-step state transitions.

2. **Overengineering:** The `hook_output.py` module defines `PreToolUseOutput`, `PostToolUseOutput`, `StopOutput`, `UserPromptSubmitOutput`, `DecisionControl`, `PermissionRequestHSO`, and `PermissionRequestHSODecision` models, but none of them appear to be used anywhere in the codebase. The hooks build output dicts manually rather than using these models.

3. **The `project_manager.py`** is the most mature and well-structured file in the codebase, with proper input validation, consistent error handling, and clean separation of concerns. It stands in contrast to the workflow hooks system which has numerous bugs.

---

## Recommendations

1. Fix all Critical findings (C-1 through C-5) immediately -- these are runtime crashes.
2. Fix all High findings (H-1 through H-7) -- these cause silent data corruption or incorrect behavior.
3. Standardize the `fully_blocked.exception` data format across all files to consistently use `list[list[str]]`.
4. Replace `sys.path` manipulation with proper package installation.
5. Add integration tests that exercise full hook lifecycle (the existing tests appear to be mostly stubs or outdated based on deleted files in git status).
6. Remove or use the `hook_output.py` models to avoid dead code accumulation.
