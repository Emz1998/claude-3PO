# Plan: Create `/build` Command

## Context

`/implement` is tied to story IDs and `project_manager.py`. We need a `/build` command that follows the same workflow (explore → plan → code → validate → PR → CI → report) but is driven purely by free-text instructions — no story ID, no project manager lookup, no task-create phase.

## Approach

### 1. Copy `workflow/` → `build/`

Create `.claude/hooks/build/` as a copy of `.claude/hooks/workflow/`. This gives us an independent hook system for `/build` that can diverge without breaking `/implement` or `/plan`.

### 2. Revise `build/` — remove story-specific logic

**`build/utils/initializer.py`**:
- Remove `parse_story_id()`, `check_story_conflict()`
- `build_initial_state()`: hardcode `story_id=None`, remove story ID parsing
- `initialize()`: remove conflict check branch

**`build/recorder.py`**:
- `advance_after_plan_approval()`: remove `story_id` → `task-create` branch (build never has tasks)

**`build/guards/task_guard.py`**: Delete — no task-create phase in build

**`build/guards/agent_guard.py`**: Remove task-create references if any

**`build/reminder.py`**: Remove task-create reminders from `EXIT_PLAN_MODE_REMINDERS`

**`build/guardrail.py`**:
- Remove `task_guard` import and dispatch route
- Remove `TaskCompleted` event handling

**`build/config/constants.py`**: No changes needed (phase sets don't include task-create for gating)

### 3. Create `.claude/commands/build.md`

- Initializer: `!python3 .claude/hooks/build/utils/initializer.py build ${CLAUDE_SESSION_ID} $ARGUMENTS`
- No `project_manager.py` call, no Story Context section
- Instructions come from `$ARGUMENTS`
- Workflow skips task-create phase entirely
- Report metadata: `task_description` instead of `story_implemented`

### 4. Register hooks for build

The build system needs its own hook registrations in `.claude/settings.json` (or project settings) pointing to `.claude/hooks/build/guardrail.py`, `.claude/hooks/build/recorder.py`, and `.claude/hooks/build/reminder.py`.

Alternatively, the existing workflow hooks can be reused if the guardrail/recorder/reminder already handle the `build` workflow type gracefully (they do — non-`"plan"` types follow the implement path, and no `story_id` means task-create is skipped). In that case, only the command file and initializer need to be separate.

**Decision**: Full copy. Independent codebase under `.claude/hooks/build/` that can diverge freely.

## Files to Create

| File | Source | Changes |
|------|--------|---------|
| `.claude/hooks/build/` | Copy of `workflow/` | Story-specific logic removed |
| `.claude/commands/build.md` | Based on `implement.md` | No story context, instruction-driven |

## Files NOT Modified

Everything under `.claude/hooks/workflow/` stays untouched.

## Verification

1. Run `python3 .claude/hooks/build/utils/initializer.py build test-session --skip-all --tdd build a login form` — verify state has `workflow_type="build"`, `story_id=None`, `tdd=True`
2. Run build tests: `pytest .claude/hooks/build/tests/`
3. Run workflow tests to confirm nothing broke: `pytest .claude/hooks/workflow/tests/`
