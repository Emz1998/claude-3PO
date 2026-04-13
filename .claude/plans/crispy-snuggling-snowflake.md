# Plan: Dual Workflow + TaskCreated + Auto-Commit + Project Manager

## Context

claudeguard currently has a single workflow used by both `/build` and `/implement`. We need to split them into two distinct workflows with different phase lifecycles, task sourcing, and guardrail behavior. Additionally, we need to copy auto-commit (with headless Claude) and project_manager into claudeguard so it's self-contained.

### User Decisions (from Q&A)

- **Build**: keeps current 14-phase workflow as-is (with install-deps, define-contracts, plan template extraction)
- **Implement**: new 13-phase workflow with project_manager task sourcing, story_id required
- **Implement auto-phases**: create-tasks, write-tests, write-code are auto-transition (skill calls blocked)
- **Implement plan template**: requires `## Context`, `## Approach`, `## Files to Create/Modify`, `## Verification` — enforced but not extracted
- **Implement file guard**: write-code blocks files NOT listed in `## Files to Create/Modify`
- **Task source**: implement uses project_manager.py (requires story_id), build uses plan `## Tasks` bullets
- **Auto-commit**: headless Claude, fires on TaskCompleted for both workflows
- **Project manager**: copy into claudeguard/ (self-contained)
- **Config**: shared config.toml with `BUILD_PHASES` and `IMPLEMENT_PHASES`
- **Explore/Research**: both workflows use 3 Explore + 2 Research in parallel
- **Plan-review checkpoint**: both workflows discontinue on pass
- **TDD**: both workflows support TDD (create-tasks → write-tests if TDD, else write-code)
- **Write-report**: skill (manual) in both workflows
- **create-tasks advance**: waits for subtasks (like workflow/ system)

---

## Step 1: Config split — BUILD_PHASES vs IMPLEMENT_PHASES

### `scripts/config/config.toml`

```toml
BUILD_PHASES = ["explore", "research", "plan", "plan-review", "install-deps", "define-contracts", "write-tests", "test-review", "write-code", "quality-check", "code-review", "pr-create", "ci-check", "write-report"]

IMPLEMENT_PHASES = ["explore", "research", "plan", "plan-review", "create-tasks", "write-tests", "tests-review", "write-code", "validate", "code-review", "pr-create", "ci-check", "write-report"]

# Phases that auto-transition (no skill commands — both workflows)
AUTO_PHASES = ["create-tasks", "write-tests", "write-code"]

# Delete commands/write-tests.md and commands/write-code.md.
# Both build and implement auto-transition into these phases via resolvers.
# Build: plan-review pass → install-deps → define-contracts → (auto) write-tests → ...
# Implement: create-tasks done → (auto) write-tests → ...
# No /create-tasks skill either — implement only, auto-transition.
```

Add to `[REQUIRED_AGENTS]`:
```toml
create-tasks = ""
validate = "QASpecialist"
tests-review = "TestReviewer"
```

Add to `[FILE_PATHS]`:
```toml
IMPLEMENT_PLAN_TEMPLATE = "implement"
BUILD_PLAN_TEMPLATE = "build"
```

### `scripts/config/config.py`

Add properties:
- `build_phases` → `BUILD_PHASES` list
- `implement_phases` → `IMPLEMENT_PHASES` list
- `auto_phases` → `AUTO_PHASES` list
- `get_phases(workflow_type: str)` → returns the right list based on `"build"` or `"implement"`

### `scripts/utils/validators.py`

Update `is_phase_allowed()`:
- Use `config.get_phases(state.get("workflow_type"))` instead of `config.main_phases`
- Block skill calls for phases in `config.auto_phases`

---

## Step 2: Implement plan template

### `claudeguard/templates/implement-plan.md` (NEW)

```markdown
# {Plan Title}

## Context
{Background and motivation}

## Approach
{High-level implementation strategy}

## Files to Create/Modify
| Action | Path |
|--------|------|
| {Create/Modify} | {file path} |

## Verification
{How to test the implementation}
```

### `scripts/utils/validators.py`

Add `IMPLEMENT_PLAN_REQUIRED_SECTIONS = ["## Context", "## Approach", "## Files to Create/Modify", "## Verification"]`

Update `_validate_plan_content()`:
- Accept `workflow_type` parameter
- If `"build"`: validate current sections (Dependencies, Contracts, Tasks) + bullet format
- If `"implement"`: validate Context, Approach, Files to Create/Modify, Verification (presence only, no extraction)

### `scripts/utils/extractors.py`

Add `extract_plan_files_to_modify(content: str) -> list[str]`:
- Reuses existing `extract_md_sections()` (line 80) to find the `## Files to Create/Modify` section
- Reuses existing `extract_table()` (line 99) to parse the markdown table and extract file paths from the Path column
- No new parsing logic — composition of two existing functions

### `scripts/utils/recorder.py`

Add `record_plan_files(file_path: str, state: StateStore) -> None`:
- On plan write for implement workflow: extract files from `## Files to Create/Modify` and store in `state.code_files_to_write`

### `scripts/post_tool_use.py`

On plan Write for implement workflow: call `record_plan_files()` after `inject_plan_metadata()`

---

## Step 3: Write-code file guard (implement only)

### `scripts/utils/validators.py`

Update `is_file_write_allowed()` for `write-code` phase:
- If workflow_type is `"implement"`: check `state.code_files_to_write`
- Block if file not in that list
- Build workflow keeps current behavior (any code extension allowed)

---

## Step 4: create-tasks phase (implement only)

### `scripts/models/state.py`

Add `Task` model:
```python
class Task(BaseModel):
    id: str
    subject: str
    status: Literal["pending", "completed"] = "pending"
    subtasks: list[dict] = []
```

Update `State`:
- Change `tasks: list[str] = []` to `tasks: list[str] | list[dict] = []` — build uses `list[str]`, implement uses `list[dict]`

### `scripts/utils/state_store.py`

Add:
- `set_project_tasks(tasks: list[dict])` — bulk setter for implement tasks
- `add_subtask(parent_task_id: str, subtask: dict)` — append subtask to parent
- `all_tasks_have_subtasks` property — check if every task has ≥1 subtask
- `mark_subtask_completed(subject: str)` — mark subtask done, auto-complete parent if all done

### `scripts/utils/validators.py`

Add `is_task_create_allowed()`:
- Only during `create-tasks` phase
- Requires `metadata.parent_task_id` and `metadata.parent_task_title`
- Validates parent_task_id exists in state tasks
- Validates parent_task_title matches

Register in `TOOL_GUARDS` for `TaskCreate` tool.

### `scripts/utils/recorder.py`

Add `record_task_create(hook_input: dict, state: StateStore)`:
- Extract subject, description from tool_input
- Extract parent_task_id from metadata
- Append subtask to parent task

### `scripts/utils/resolvers.py`

Add `resolve_create_tasks(state: StateStore)`:
- Complete when `state.all_tasks_have_subtasks`
- Auto-advance to `write-tests` if TDD, else `write-code`

### `scripts/guardrails/task_create_guard.py` (NEW)

Wire `is_task_create_allowed()` → `record_task_create()`.

### Phase initialization

When `plan-review` completes for implement workflow:
- Fetch project tasks via `project_manager.py view <story_id> --tasks --json`
- Store in `state.tasks` as `list[dict]`
- Auto-start `create-tasks` phase

---

## Step 5: Auto-transition phases

### `scripts/utils/resolvers.py`

Update `resolve()`:
- After completing plan-review (implement): auto-start create-tasks + fetch project tasks
- After completing create-tasks: auto-start write-tests (if TDD) or write-code
- After completing tests-review: auto-start write-code

### No skill blocking needed

Auto-phases (create-tasks, write-tests, write-code) simply have no `/skill` command files. Claude can't invoke them because the commands don't exist. The resolver auto-starts these phases when the previous phase completes.

### `scripts/pre_tool_use.py`

Add `TaskCreate` to `TOOL_GUARDS` dispatch.

---

## Step 6: validate phase (implement)

This is the same as quality-check but renamed for implement. The resolver and recorder logic is identical — `QASpecialist` agent, Pass/Fail verdict.

### `scripts/utils/resolvers.py`

Add `resolve_validate` (alias for `resolve_quality_check`):
```python
"validate": lambda: resolve_quality_check(state),
```

---

## Step 7: Copy project_manager into claudeguard

### `claudeguard/github_project/` (NEW directory)

Copy from `/home/emhar/avaris-ai/github_project/`:
- `config.py`
- `project_manager.py`
- `sync_project.py`
- `utils/gh_utils.py`
- `utils/__init__.py`
- `issues/` directory (sprint.json, stories.json)
- `templates/` directory

### Config adaptation

Update `config.py` paths to be relative to the new location inside claudeguard.

---

## Step 8: Copy auto-commit + headless Claude into claudeguard

### `claudeguard/scripts/auto_commit.py` (NEW)

Copy from `/home/emhar/avaris-ai/.claude/hooks/workflow/auto_commit.py`.

Adapt:
- Import paths: use claudeguard's `config`, `utils.hook`, `utils.state_store`
- Batch ledger path: add `COMMIT_BATCH_PATH` to config.toml `[FILE_PATHS]`
- Log calls: use claudeguard's logging approach

### `claudeguard/scripts/headless_claude/` (NEW directory)

Copy from `/home/emhar/avaris-ai/.claude/hooks/workflow/headless_claude/`:
- `__init__.py`
- `claude.py`

Adapt:
- `TEMPLATE_DIR` path to point to claudeguard prompts

### `claudeguard/scripts/prompts/` (NEW directory)

Copy commit message prompt template from workflow/.

### `claudeguard/hooks/hooks.json`

Add `TaskCompleted` hook entry pointing to `auto_commit.py`.

---

## Step 9: Update task_created.py

### `scripts/task_created.py`

Update to handle both workflows:
- **Build**: current behavior (fuzzy match against plan `## Tasks` bullets)
- **Implement**: validate `metadata.parent_task_id` + `metadata.parent_task_title` against project tasks (same as workflow/ task_guard)

---

## Step 10: Update commands

### `commands/implement.md`

Rewrite to reflect new 13-phase workflow:
- explore + research (parallel, skills)
- plan (skill)
- plan-review (skill, checkpoint)
- create-tasks (auto — fetch from project_manager, create subtasks)
- write-tests (auto, TDD only)
- tests-review (skill)
- write-code (auto)
- validate (skill — QASpecialist)
- code-review (skill)
- pr-create (skill)
- ci-check (skill)
- write-report (skill)

Reference implement plan template.

### `commands/build.md`

Update to reflect auto-transition for write-tests and write-code:
- Remove `/write-tests` and `/write-code` as skill steps
- Document them as auto-transition phases (resolver starts them after define-contracts completes)
- Skill phases for build: `/explore`, `/research`, `/plan`, `/plan-review`, `/install-deps`, `/define-contracts`, `/test-review`, `/quality-check`, `/code-review`, `/pr-create`, `/ci-check`, `/write-report`

### `commands/write-tests.md` and `commands/write-code.md`

Delete both files. These are now auto-transition phases for both workflows.

### `commands/validate.md` (NEW)

Same as quality-check.md but for implement workflow.

### Commands NOT created (auto-phases)

No command files for `create-tasks`, `write-tests` (implement), or `write-code` (implement). These phases auto-transition via resolvers — no skill invocation exists.

---

## Step 11: Update initializer

### `scripts/utils/initializer.py`

Update `build_initial_state()`:
- If workflow_type is `"implement"`: require story_id, raise error if missing
- Tasks field: `[]` for both (populated later — build from plan extraction, implement from project_manager)

---

## Step 12: Update dry_run and tests

### `scripts/tests/dry_run.py`

Add implement workflow simulation alongside existing build simulation.

### Unit tests

- Test implement phase ordering
- Test auto-phase skill blocking
- Test create-tasks validation (parent_task_id matching)
- Test create-tasks auto-advance (all tasks have subtasks)
- Test implement plan template validation
- Test write-code file guard (implement: blocks unlisted files)
- Test validate resolver
- Test task_created for both workflows

---

## Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `scripts/config/config.toml` | Modify | Add IMPLEMENT_PHASES, AUTO_PHASES, new agents |
| `scripts/config/config.py` | Modify | Add workflow-type-aware phase accessors |
| `scripts/models/state.py` | Modify | Add Task model |
| `scripts/utils/state_store.py` | Modify | Add project task setters, subtask tracking |
| `scripts/utils/validators.py` | Modify | Workflow-aware phase validation, auto-phase blocking, file guard, task_create validation |
| `scripts/utils/extractors.py` | Modify | Add extract_plan_files_to_modify |
| `scripts/utils/recorder.py` | Modify | Add task_create recording, plan files recording |
| `scripts/utils/resolvers.py` | Modify | Add create-tasks, validate resolvers, auto-transitions |
| `scripts/utils/initializer.py` | Modify | story_id required for implement |
| `scripts/post_tool_use.py` | Modify | Plan files extraction for implement |
| `scripts/pre_tool_use.py` | Modify | Add TaskCreate guard |
| `scripts/task_created.py` | Modify | Dual workflow handling |
| `scripts/auto_commit.py` | Create | Auto-commit on TaskCompleted |
| `scripts/headless_claude/` | Create | Headless Claude for commit messages |
| `scripts/prompts/` | Create | Commit message prompt template |
| `scripts/guardrails/__init__.py` | Modify | Register TaskCreate guard |
| `scripts/guardrails/task_create_guard.py` | Create | TaskCreate guardrail handler |
| `templates/implement-plan.md` | Create | Implement plan template |
| `claudeguard/github_project/` | Create | Copy of project_manager |
| `hooks/hooks.json` | Modify | Add TaskCompleted hook |
| `commands/implement.md` | Modify | New 13-phase workflow |
| `commands/validate.md` | Create | Validate phase command |
| `scripts/tests/dry_run.py` | Modify | Add implement simulation |
| `scripts/tests/` | Modify | New tests for all changes |

## Verification

1. **Unit tests**: Run `python -m pytest tests/ -v` — all existing + new tests pass
2. **Dry run (build)**: `python tests/dry_run.py` — 50+ checks pass
3. **Dry run (implement)**: `python tests/dry_run.py --implement` — new implement flow passes
4. **Dry run (TDD)**: `python tests/dry_run.py --tdd` — TDD variant passes
5. **Auto-commit**: Verify TaskCompleted hook triggers auto_commit.py
6. **Project manager**: Verify `python github_project/project_manager.py view SK-001 --tasks --json` works from claudeguard/
