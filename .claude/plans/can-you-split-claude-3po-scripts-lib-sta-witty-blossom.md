# Split `state_store.py` into workflow-specific state classes

## Context

`claude-3PO/scripts/lib/state_store.py` has grown to **2995 lines / 122 methods** on one class. Roughly 10% of the methods are workflow-specific — five for the **build** workflow, nine for **implement**, six for **specs** — and the rest are shared core (I/O, phases, agents, plan, tests, code, PR, CI, report). Keeping all three workflows' surface area on a single class violates the project's module-SRP rule and makes it hard to reason about which fields belong to which workflow.

Splitting it into `BuildState`, `ImplementState`, `SpecsState` (plus a shared `BaseState`) and keeping `StateStore` as a **composition-based facade** with **named sub-attributes** achieves:
- **Explicit workflow ownership at every call site** — readers see `state.implement.project_tasks` and immediately know which workflow owns that field.
- **Clear module boundaries** — each workflow's slice lives in its own file.
- **Single file, single lock** — the three workflow classes delegate I/O through one shared `BaseState`, preserving the atomic read-modify-write guarantee.

This is composition, not inheritance: `state.build`, `state.implement`, `state.specs` are named attributes on the facade — not a flat `__getattr__` fallback. Callers that today write `state.project_tasks` will rewrite to `state.implement.project_tasks`. The churn is the cost of making ownership visible.

## Scope — which methods move where

Verified via Explore agent against all callers under `claude-3PO/scripts/`.

### `BaseState` — shared core (stays reachable as `state.<method>`)
- **Core I/O**: `__init__`, `session_id`, `_read_all_lines`, `_write_all_lines`, `_find_session`, `load`, `save`, `update`, `load_model`, `save_model`, `get`, `set`, `set_many`, `reinitialize`, `delete`, `_is_active_for_story`, `find_active_by_story`, `deactivate_by_story`, `cleanup_inactive`
- **Phases** (all 8 methods — every workflow uses phases)
- **Plan revision tracking**, **Code revision tracking**, **Code-review test revision tracking**
- **Agents** (all 8 methods)
- **Plan**, **Tests**, **Code files** (review/revision state — shared)
- **Test revision tracking**, **Code files to write**
- **Quality check**, **PR**, **CI**, **Report**, **Tasks**
- **Flat-API sinks** (except workflow-specific ones): `_replace_in_section`, `_append_unique_in_section`, `add_command`, `add_validation`, `add_code_review_record`, `add_test_review_record`, `set_test_mode`, `set_report_file_path`, `set_tdd`, `set_plan_reviews`, `set_test_reviews`, `set_code_reviews`, `set_test_file_paths`, `set_code_file_paths`, `set_test_files_revised`, `set_code_files_revised`, `add_test_file_to_revise`, `add_code_file_to_revise`

### `BuildState` — accessed as `state.build.<method>`
- `created_tasks`, `add_created_task`
- `get_clarify_phase`, `set_clarify_session`, `bump_clarify_iteration`

### `ImplementState` — accessed as `state.implement.<method>`
- `project_tasks`, `set_project_tasks`, `add_subtask`, `set_subtask_completed`, `set_project_task_completed`, `get_parent_for_subtask`
- `plan_files_to_modify`, `set_plan_files_to_modify`
- `add_project_task` (flat-API sink — consumed by `Recorder.record_task`)

### `SpecsState` — accessed as `state.specs.<method>`
- `docs`, `set_doc_written`, `set_doc_path`, `set_doc_md_path`, `set_doc_json_path`, `is_doc_written`

## Design — composition with named sub-attributes

```
BaseState (Path, session_id, lock, JSONL I/O, shared methods)
   ▲ referenced by
   │
BuildState(base)      ImplementState(base)      SpecsState(base)
   (thin wrappers — delegate load/update to base)

StateStore(BaseState)
   ├── .build     = BuildState(self)
   ├── .implement = ImplementState(self)
   └── .specs     = SpecsState(self)
```

- **`StateStore` inherits `BaseState`**, so `state.load()`, `state.phases`, `state.add_agent(...)` etc. all still work on the facade directly — zero churn for shared methods.
- In `__init__`, after super-initing, the facade constructs the three workflow wrappers passing `self` as the base reference.
- The wrappers hold `self._base` and call through: e.g. `ImplementState.project_tasks` returns `self._base.load().get("project_tasks", [])`; `ImplementState.add_subtask(...)` calls `self._base.update(_add)`.
- **No `__getattr__` magic** — every accessor is explicit.

### Example call-site translations

| Today | After |
|-------|-------|
| `state.load()`, `state.phases`, `state.add_agent(...)` | **unchanged** (shared, on BaseState) |
| `state.created_tasks` | `state.build.created_tasks` |
| `state.add_created_task(subj)` | `state.build.add_created_task(subj)` |
| `state.get_clarify_phase()` | `state.build.get_clarify_phase()` |
| `state.project_tasks` | `state.implement.project_tasks` |
| `state.add_subtask(...)` | `state.implement.add_subtask(...)` |
| `state.set_project_tasks(...)` | `state.implement.set_project_tasks(...)` |
| `state.plan_files_to_modify` | `state.implement.plan_files_to_modify` |
| `state.add_project_task(task)` | `state.implement.add_project_task(task)` |
| `state.docs` | `state.specs.docs` |
| `state.set_doc_written(k, v)` | `state.specs.set_doc_written(k, v)` |
| `state.is_doc_written(k)` | `state.specs.is_doc_written(k)` |

Cross-workflow access stays natural: `resolver.py`'s `_resolve_create_tasks` branches on `workflow_type` and calls `self.state.build.created_tasks` in one branch, `self.state.implement.project_tasks` in the other. Ownership is now visible in the code, not implicit.

## File layout

Replace the flat `claude-3PO/scripts/lib/state_store.py` module with a package at `claude-3PO/scripts/lib/state_store/`:

```
claude-3PO/scripts/lib/state_store/
├── __init__.py    — re-exports StateStore, BaseState, BuildState,
│                    ImplementState, SpecsState
├── base.py        — BaseState class (~1900 lines, the shared bulk)
├── build.py       — BuildState class (~80 lines)
├── implement.py   — ImplementState class (~180 lines)
├── specs.py       — SpecsState class (~120 lines)
└── store.py       — StateStore facade (~40 lines):
                      inherits BaseState, composes the three wrappers
```

**Import compatibility**: `__init__.py` re-exports `StateStore`, so every existing
`from lib.state_store import StateStore` call site continues to resolve with zero
changes. The old flat `state_store.py` file is deleted as part of the package
creation — nothing else in the repo imports it directly.

## Critical files to modify

### 1. `lib/state_store.py` — replace with `lib/state_store/` package
Delete the flat module; create the package with `__init__.py`, `base.py`, `build.py`, `implement.py`, `specs.py`, `store.py` as described in "File layout".

### 2. Production callers that reference workflow-specific methods — 9 files
| File | Calls to rewrite |
|------|------------------|
| `guardrails/phase_guard.py` | `get_clarify_phase` → `state.build.get_clarify_phase` |
| `guardrails/write_guard.py` | `plan_files_to_modify` → `state.implement.plan_files_to_modify`; docs access → `state.specs.docs` |
| `guardrails/task_created_guard.py` | `project_tasks` → `state.implement.project_tasks` |
| `guardrails/task_create_tool_guard.py` | `project_tasks` → `state.implement.project_tasks` |
| `utils/resolver.py` | `created_tasks` → `state.build.created_tasks`; `project_tasks` → `state.implement.project_tasks`; `is_doc_written` → `state.specs.is_doc_written` |
| `utils/recorder.py` | `add_project_task` → `state.implement.add_project_task` |
| `dispatchers/post_tool_use.py` | `get_clarify_phase`, `bump_clarify_iteration` → `state.build.*` |
| `dispatchers/task_created.py` | `add_created_task` → `state.build.add_created_task`; `add_subtask`, `project_tasks` → `state.implement.*` |
| `dispatchers/task_completed.py` | `get_parent_for_subtask`, `project_tasks`, `set_subtask_completed`, `set_project_task_completed` → `state.implement.*` |

### 3. Tests that reference workflow-specific methods — 12 files
`tests/test_state_store.py`, `tests/test_build_create_tasks.py`, `tests/test_create_tasks.py`, `tests/test_task_lifecycle.py`, `tests/test_task_created.py`, `tests/test_recorders.py`, `tests/test_clarify_phase.py`, `tests/test_auto_transition.py`, `tests/test_file_guard.py`, `tests/test_specs_resolver.py`, `tests/test_decision_build_phase.py`, `tests/helpers.py`

Mechanical rewrite: `state.<method>` → `state.build.<method>` / `state.implement.<method>` / `state.specs.<method>` per the bucket table.

## Files that will **not** need to change

- `dispatchers/pre_tool_use.py`, `dispatchers/subagent_stop.py`, `utils/initializer.py`, `utils/summarize_prompt.py`, `lib/extractors.py`, `guardrails/__init__.py`, `guardrails/edit_guard.py`, `guardrails/command_validator.py`, `guardrails/stop_guard.py` — they only touch shared methods (`load`, `set`, `phases`, `agents`, etc.) which remain on `BaseState`.
- `models/state.py` — on-disk JSONL format is unchanged.

## TDD test plan

Per CLAUDE.md, tests are revised first, then implementation.

1. **Rewrite existing tests first** — update the 12 test files to use `state.build.*` / `state.implement.*` / `state.specs.*`. Run suite to confirm they fail (classes don't exist yet).
2. **Add one new test module per new class** — `test_base_state.py`, `test_build_state.py`, `test_implement_state.py`, `test_specs_state.py` — each proving:
   - Standalone instantiation works (BaseState).
   - Wrapper classes delegate reads/writes through the shared BaseState (one file, one lock).
   - Accessing a wrong-workflow attribute on a StateStore still works — `state.build` is always present regardless of `workflow_type` (facade is workflow-agnostic).
3. **Implement `BaseState` first**, run `test_base_state.py` + all shared-method tests from `test_state_store.py` → all green before touching workflow wrappers.
4. **Implement each wrapper + rewrite the corresponding production callers**, one workflow at a time (build → implement → specs). Run the matching test file after each slice; stop & fix before moving on.
5. **Final full-suite run**:
   ```
   python -m pytest claude-3PO/scripts/tests/ -q
   ```
6. **Smoke-check** an end-to-end flow: trigger a PostToolUse hook against a sample fixture to confirm dispatchers still drive the facade correctly.

## Verification

- `python -m pytest claude-3PO/scripts/tests/ -q` — all green.
- `grep -rn "state\.\(project_tasks\|created_tasks\|docs\|get_clarify_phase\)" claude-3PO/scripts/ --include="*.py" | grep -v "lib/"` — should return **zero** matches (all bare accesses migrated to namespaced form).
- `grep -rn "from lib.state_store import" claude-3PO/scripts/` — every match still resolves.
- Spot-check resolver's cross-workflow branch: fabricate a `workflow_type == "build"` state and a `workflow_type == "implement"` state; confirm both `state.build.created_tasks` and `state.implement.project_tasks` paths work through the facade.
- Docstring + inline-comment conventions (Args / Returns / SideEffect / Example) preserved on every migrated method — no docstrings rewritten, just relocated.

## Out of scope

- Splitting `models/state.py` into per-workflow Pydantic models.
- Refactoring `resolver.py` / recorder / guards to stop branching on `workflow_type`.
- Changing any on-disk JSONL format.
- Adding type-narrowing (e.g. `StateStore[Build]` generics) — keep it a concrete class.
