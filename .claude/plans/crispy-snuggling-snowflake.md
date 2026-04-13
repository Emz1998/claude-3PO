# Plan: Dual Workflow + Auto-Commit + Project Manager

## Context

claudeguard currently has a single workflow for both `/build` and `/implement`. We need to split them into two distinct workflows, migrate state from JSON to session-scoped JSONL, copy auto-commit and project_manager into claudeguard, and introduce auto-transitioning phases.

## Decisions

- **Build**: keeps current 14-phase workflow (install-deps, define-contracts, plan template extraction)
- **Implement**: new 13-phase workflow with project_manager tasks, story_id required
- **Auto-phases**: create-tasks, write-tests, write-code — no skill commands, resolver auto-transitions. Applies to both workflows. Delete `commands/write-tests.md` and `commands/write-code.md`.
- **Task source**: implement uses project_manager (story_id required), build uses plan `## Tasks` bullets
- **Plan template**: build enforces Dependencies/Contracts/Tasks (with extraction). Implement enforces Context/Approach/Files to Create-Modify/Verification (no extraction, except files list for write-code guard).
- **Write-code file guard** (implement only): blocks writes to files NOT in `## Files to Create/Modify`
- **Auto-commit**: headless Claude on TaskCompleted, both workflows
- **State**: migrate StateStore from single JSON to session-scoped JSONL
- **Config**: shared config.toml with BUILD_PHASES and IMPLEMENT_PHASES
- **Plan-review checkpoint**: both workflows discontinue on pass
- **create-tasks**: waits for all project tasks to have subtasks before advancing
- **validate**: same as quality-check (QASpecialist), renamed for implement

## Implement Phase Flow

```
/explore + /research (parallel, skills)
  → /plan (skill)
  → /plan-review (skill, checkpoint — discontinue on pass)
  → create-tasks (auto — fetch from project_manager, wait for subtasks)
  → write-tests (auto, TDD only)
  → /tests-review (skill)
  → write-code (auto)
  → /validate (skill — QASpecialist)
  → /code-review (skill)
  → /pr-create (skill)
  → /ci-check (skill)
  → /write-report (skill)
```

## Build Phase Flow (unchanged)

```
/explore + /research (parallel, skills)
  → /plan (skill)
  → /plan-review (skill, checkpoint)
  → /install-deps (skill)
  → /define-contracts (skill)
  → write-tests (auto, TDD only)
  → /test-review (skill)
  → write-code (auto)
  → /quality-check (skill)
  → /code-review (skill)
  → /pr-create (skill)
  → /ci-check (skill)
  → /write-report (skill)
```

## Steps

### 1. Migrate StateStore to JSONL

- Modify `StateStore` to take `session_id` in constructor, operate on JSONL (one line per session)
- Keep all existing properties/setters unchanged
- Add `cleanup_inactive()` classmethod, called during `initialize()`
- Update all entry points to pass `session_id` from `hook_input`
- Update tests/conftest and dry_run for JSONL

### 2. Config split

- Add `BUILD_PHASES`, `IMPLEMENT_PHASES`, `AUTO_PHASES` to config.toml
- Add `get_phases(workflow_type)` to Config class
- Add implement-specific required agents (validate = QASpecialist, tests-review = TestReviewer, create-tasks = none)

### 3. Implement plan template

- Create `templates/implement-plan.md` (Context, Approach, Files to Create/Modify, Verification)
- Update `_validate_plan_content()` to dispatch by workflow_type
- Add `extract_plan_files_to_modify()` — reuses existing `extract_md_sections()` + `extract_table()`

### 4. Write-code file guard

- For implement workflow: block writes to files not in `## Files to Create/Modify` list
- Build workflow keeps current behavior (any code extension)

### 5. create-tasks phase

- On plan-review pass (implement): fetch project tasks via `project_manager.py view <story_id> --tasks --json`, store in state
- Validate TaskCreate has `metadata.parent_task_id` + `metadata.parent_task_title` matching project tasks
- Record subtasks under parent tasks
- Auto-advance when all project tasks have ≥1 subtask → write-tests (TDD) or write-code

### 6. Auto-transition phases

- Delete `commands/write-tests.md` and `commands/write-code.md`
- Resolvers auto-start write-tests/write-code after previous phase completes (both workflows)
- Resolvers auto-start create-tasks after plan-review (implement only)

### 7. Copy project_manager into claudeguard

- Copy `github_project/` into `claudeguard/github_project/`
- Adapt config paths to be relative to new location

### 8. Copy auto-commit + headless Claude

- Copy `auto_commit.py` and `headless_claude/` into claudeguard
- Adapt imports to claudeguard's structure
- Add TaskCompleted hook to `hooks.json`

### 9. Update commands

- Rewrite `commands/implement.md` for new 13-phase workflow
- Update `commands/build.md` for auto-transition write-tests/write-code
- Create `commands/validate.md`
- Delete `commands/write-tests.md`, `commands/write-code.md`

### 10. Tests and dry_run

- Update all existing tests for JSONL StateStore
- Add implement workflow tests (phase ordering, create-tasks, file guard, plan template)
- Add implement dry_run simulation (`--implement` flag)

## Approach: TDD

For each step, write failing tests first, then implement to make them pass.

### Test order (mirrors steps)

1. **StateStore JSONL tests** — session isolation, load/save/update by session_id, cleanup_inactive, all existing property tests adapted
2. **Config tests** — BUILD_PHASES, IMPLEMENT_PHASES, AUTO_PHASES, get_phases()
3. **Implement plan template tests** — required sections validation, extract_plan_files_to_modify
4. **Write-code file guard tests** — implement blocks unlisted files, build allows any code extension
5. **create-tasks tests** — TaskCreate validation (parent_task_id/title matching), subtask recording, auto-advance when all covered
6. **Auto-transition tests** — resolver auto-starts write-tests/write-code/create-tasks, phase ordering
7. **Dry run tests** — implement simulation, implement TDD simulation

## Verification

- `python -m pytest tests/ -v` — all tests pass
- `python tests/dry_run.py` — build flow
- `python tests/dry_run.py --tdd` — build TDD flow
- `python tests/dry_run.py --implement` — implement flow
- `python tests/dry_run.py --implement --tdd` — implement TDD flow
