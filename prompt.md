# Workflow Hooks: Multi-Session Architecture Implementation

## Context

The current workflow hooks system uses a **flat state model** — a single `state.json` tracking one active story at a time with top-level keys like `recent_agent`, `recent_phase`, `story`, `validation`. The architecture.md spec requires a **multi-session model** where `state.json` holds a `sessions` dict keyed by story ID (`SK-001`) or PR key (`PR-42`), enabling parallel worktree sessions via tmux.

Additionally, several hooks described in the architecture don't exist yet (hold_checker, bash_guard, review_trigger, session_logger, etc.), the phase guard approach needs to move from settings.local.json to skill frontmatter, and the code-reviewer agent needs additional Stop hooks.

---

## Phase 1: Session State Layer (Foundation)

### 1.1 RED — Write failing tests for `SessionState`

**File**: `.claude/hooks/workflow/tests/test_session_state.py` (NEW)

Uses `tmp_path` fixture (like `test_state_store.py`). Tests use a real `StateStore` backed by temp file — no mocking needed for the core class.

```python
class TestSessionStateCreate:
    def test_create_session_stores_under_sessions_key(self, tmp_path)
    def test_create_duplicate_raises_or_overwrites(self, tmp_path)

class TestSessionStateGet:
    def test_get_existing_session(self, tmp_path)
    def test_get_nonexistent_returns_none(self, tmp_path)

class TestSessionStateUpdate:
    def test_update_modifies_session_in_place(self, tmp_path)
    def test_update_nonexistent_raises(self, tmp_path)

class TestSessionStateDelete:
    def test_delete_removes_session_key(self, tmp_path)
    def test_delete_nonexistent_is_noop(self, tmp_path)

class TestSessionStateDefaults:
    def test_default_implement_session_has_required_keys(self)
    def test_default_pr_review_session_has_required_keys(self)

class TestSessionStateNoStoryId:
    def test_story_id_none_when_env_not_set(self, tmp_path)
    def test_story_id_reads_from_env(self, tmp_path, monkeypatch)
```

### 1.2 GREEN — Implement `session_state.py`

**File**: `.claude/hooks/workflow/session_state.py` (NEW)

Session-scoped wrapper around `StateStore`. All hooks will use this instead of raw `StateStore` for session data.

```python
class SessionState:
    def __init__(self):
        self._store = StateStore(cfg("paths.workflow_state"))
        self._story_id = os.environ.get("STORY_ID")

    @property
    def story_id(self) -> str | None:
        return self._story_id

    def get_session(self, story_id: str) -> dict | None
    def update_session(self, story_id: str, fn: Callable) -> None
    def create_session(self, story_id: str, data: dict) -> None
    def delete_session(self, story_id: str) -> None

    @staticmethod
    def default_implement_session(story_id: str, session_id: str) -> dict

    @staticmethod
    def default_pr_review_session(pr_number: int, session_id: str) -> dict
```

Session template (implement):

```json
{
  "session_id": "<uuid>",
  "workflow_type": "implement",
  "story_id": "SK-001",
  "phase": { "current": "pre-coding", "previous": null, "recent_agent": null },
  "control": {
    "status": "running",
    "hold": false,
    "blocked_until_phase": null
  },
  "pr": { "created": false, "number": null },
  "validation": {
    "decision_invoked": false,
    "confidence_score": 0,
    "quality_score": 0,
    "iteration_count": 0,
    "escalate_to_user": false
  },
  "ci": { "status": "pending", "iteration_count": 0, "escalate_to_user": false }
}
```

### 1.3 Update `config.yaml`

**File**: `.claude/hooks/workflow/config.yaml` (MODIFY)

- Add `ci_max_iterations: 2` under `validation`
- Add `sessions_dir` path under `paths`

### 1.4 Update `constants/phases.py`

**File**: `.claude/hooks/workflow/constants/phases.py` (MODIFY)

- Add control status constants: `STATUS_RUNNING`, `STATUS_COMPLETED`, `STATUS_FAILED`, `STATUS_ABORTED`
- Add CI status constants: `CI_PENDING`, `CI_PASS`, `CI_FAIL`

### 1.5 Run tests — all Phase 1 tests pass

---

## Phase 2: Migrate Existing Hooks to Session-Scoped State

**Pattern for all hooks**: Import `SessionState`, get `story_id` from env, access session-scoped data. Graceful fallback when `STORY_ID` not set (return early, no-op).

### 2.1 RED — Update existing tests to use session-scoped state

**`tests/test_handlers.py`** (MODIFY) — Update existing tests:

- `TestRecorder`: Mock `SessionState` instead of flat `STATE_STORE`; assert `session.update_session()` called with phase/agent updates
- `TestPrRecorder`: Assert writes to `session.pr.created` and `session.pr.number`
- `TestInitializeState`: Assert creates session entry via `SessionState.create_session()`
- Add `TestRecordDone`: Assert sets `session.control.status = "completed"`

**`tests/test_guards.py`** (MODIFY) — Update existing tests:

- `TestCodingPhaseGuard`: Read `session.phase.recent_agent` instead of flat `recent_agent`
- `TestPreCodingPhaseGuard`: Same session-scoped reads
- `TestStopGuard`: Check `session.control.status`, `session.pr.created`, `session.ci.status`

**`tests/test_validation_loop.py`** (MODIFY) — Update existing tests:

- Set `STORY_ID` env var in subprocess calls
- Assert validation data written to `session.validation.*` keys

**`tests/conftest.py`** (MODIFY) — Add fixtures:

- `mock_session_state`: Returns `SessionState` backed by tmp file with a pre-created session
- `story_id_env`: Sets `STORY_ID=SK-TEST` via `monkeypatch.setenv`

### 2.2 GREEN — Migrate hooks

**`handlers/implement_trigger.py`** (MODIFY)

- Call `session_state.create_session(story_id, default_implement_session(...))`
- Remove flat keys: `implement_sessions`, `pr_created`, `story`
- Set `phase.current = "pre-coding"` in session
- Keep `activate_workflow()` call

**`handlers/build_entry.py`** (MODIFY — minor)

- Already works. Just ensure `STORY_ID` env var propagation (handled by launch-claude.py)

**`handlers/recorder.py`** (MODIFY)

- Change `record("recent_agent", ...)` → `session.update_session(story_id, phase.recent_agent)`
- Change `record("recent_phase", ...)` → `session.update_session(story_id, phase.current)`
- Change `record("enter_plan_mode_triggered", ...)` → `session.update_session(story_id, phase.current = "pre-coding")`

**`handlers/phase_recorder.py`** (MODIFY)

- Session-scoped agent recording

**`handlers/pr_recorder.py`** (MODIFY)

- Change `state.set("pr_created", True)` → `session.pr.created = True, session.pr.number = N`

**`handlers/record_done.py`** (MODIFY)

- Change flat story status → `session.control.status = "completed"`

**`guards/pre_coding_phase.py`** (MODIFY)

- Read `session.phase.recent_agent` instead of flat `recent_agent`

**`guards/code_phase.py`** (MODIFY)

- Read `session.phase.recent_agent` from session

**`guards/stop_guard.py`** (MODIFY)

- Check `session.control.status`, `session.pr.created`, `session.ci.status`
- Write `session.control.status = "completed"` on allow

**`validation/decision_handler.py`** (MODIFY)

- Write to `session.validation` instead of flat `state.validation`

**`validation/decision_guard.py`** (MODIFY)

- Read `session.validation.decision_invoked`

**`validation/validation_loop.py`** (MODIFY)

- Read/write `session.validation.confidence_score`, `iteration_count`, `escalate_to_user`

**`validation/escalate.py`** (MODIFY)

- Read `session.validation.escalate_to_user`

**`lib/launch-claude.py`** (MODIFY)

- Set `STORY_ID` env var in tmux send-keys: `export STORY_ID={story_id} && claude ...`

**`initialize_state.py`** (MODIFY)

- Adapt to create session entry or be absorbed into `implement_trigger.py`

### 2.3 Run tests — all updated tests pass

---

## Phase 3: New Guards and Handlers

### 3.1 RED — Write failing tests for new guards

**File**: `.claude/hooks/workflow/tests/test_new_guards.py` (NEW)

```python
class TestPhaseGuard:
    def test_valid_transition_allows(self, tmp_path)          # pre-coding → code: exit 0
    def test_invalid_transition_blocks(self, tmp_path)        # pre-coding → push: exit 2
    def test_hold_true_blocks(self, tmp_path)                 # control.hold=True: exit 2
    def test_blocked_until_phase_blocks(self, tmp_path)       # blocked_until_phase set: exit 2
    def test_records_transition_on_success(self, tmp_path)    # phase.previous updated
    def test_no_story_id_is_noop(self, tmp_path)              # graceful no-op

class TestHoldChecker:
    def test_hold_true_blocks_agent(self, tmp_path)           # hold=True + Agent tool: exit 2
    def test_hold_true_blocks_skill(self, tmp_path)           # hold=True + Skill tool: exit 2
    def test_hold_false_allows(self, tmp_path)                # hold=False: exit 0
    def test_aborted_status_blocks(self, tmp_path)            # status="aborted": exit 2
    def test_no_story_id_allows(self, tmp_path)               # no env var: exit 0

class TestBashGuard:
    def test_gh_pr_create_blocked_outside_phase(self, tmp_path)    # phase != create-pr: exit 2
    def test_gh_pr_create_allowed_in_phase(self, tmp_path)         # phase == create-pr: exit 0
    def test_gh_pr_close_always_blocked(self, tmp_path)            # always: exit 2
    def test_gh_pr_merge_always_blocked(self, tmp_path)            # always: exit 2
    def test_git_push_blocked_outside_phase(self, tmp_path)        # phase != push: exit 2
    def test_git_push_allowed_in_phase(self, tmp_path)             # phase == push: exit 0
    def test_normal_bash_allowed(self, tmp_path)                   # ls, echo, etc: exit 0
    def test_no_story_id_allows_all(self, tmp_path)                # no env var: exit 0
```

### 3.2 RED — Write failing tests for new handlers

**File**: `.claude/hooks/workflow/tests/test_new_handlers.py` (NEW)

```python
class TestReviewTrigger:
    def test_creates_pr_review_session(self, tmp_path)        # /review 42 → sessions["PR-42"]
    def test_ignores_non_review_prompts(self, tmp_path)       # "hello" → no-op
    def test_session_has_pr_review_type(self, tmp_path)       # workflow_type == "pr-review"

class TestSessionLogger:
    def test_appends_jsonl_entry(self, tmp_path)              # log file has entry
    def test_entry_has_required_fields(self, tmp_path)        # ts, session, event, phase
    def test_no_story_id_is_noop(self, tmp_path)              # no env var → no file written

class TestSimplifyTrigger:
    def test_injects_simplify_on_new_file_in_code_phase(self, tmp_path)  # systemMessage output
    def test_skips_non_code_phase(self, tmp_path)             # no output
    def test_skips_existing_file_edit(self, tmp_path)         # no output for Edit tool

class TestCiCheckHandler:
    def test_updates_ci_status_on_pass(self, tmp_path)        # session.ci.status = "pass"
    def test_increments_iteration_on_fail(self, tmp_path)     # iteration_count += 1
    def test_escalates_at_max_iterations(self, tmp_path)      # escalate_to_user = True
    def test_ignores_non_push_skills(self, tmp_path)          # /plan → no-op

class TestCleanupTrigger:
    def test_no_cleanup_when_ci_pending(self, tmp_path)       # ci.status != "pass": no-op
    def test_cleanup_after_ci_green(self, tmp_path)           # subprocess called for worktree remove
```

### 3.3 GREEN — Implement new guards

**`guards/phase_guard.py`** (NEW) — replaces `guards/phase_transition.py`

- Takes CLI args: `python3 phase_guard.py <predecessor> <current>`
- Reads `session.phase.previous`, validates against expected predecessor
- Records transition to state on success
- Checks `session.control.hold` and `session.control.blocked_until_phase`
- Exit 0 (allow) or exit 2 (block)
- Reuses: `validate_order()` from `utils/order_validation.py`

**`guards/hold_checker.py`** (NEW)

- PreToolUse hook for Agent + Skill matchers
- Reads `session.control.hold` and `session.control.status`
- Blocks if `hold == True` or `status == "aborted"`
- Allows Read/Write/Bash to pass through (only blocks Agent/Skill)

**`guards/bash_guard.py`** (NEW)

- PreToolUse hook for Bash matcher
- Reads command from `hook_input.tool_input.command`
- Rules:
  - `gh pr create` → BLOCK unless `session.phase.current == "create-pr"`
  - `gh pr (close|merge|edit)` → BLOCK always
  - `git push` → BLOCK unless `session.phase.current == "push"`
  - Everything else → ALLOW

### 3.4 GREEN — Implement new handlers

**`handlers/review_trigger.py`** (NEW)

- UserPromptSubmit handler for `/review <pr_number>`
- Creates session keyed as `PR-<number>` with `workflow_type = "pr-review"`
- Sets `session.pr.created = True`, `session.pr.number = N`
- Sets `session.phase.current = "pr-review"`

**`handlers/session_logger.py`** (NEW)

- PostToolUse handler, no matcher (fires on all tools)
- Appends JSONL entry to `.claude/sessions/SPRINT-NNN/STORY-ID/log.jsonl`
- Entry format: `{"ts": ISO, "session": story_id, "event": tool_name, "phase": current_phase}`
- Reuses: `FileManager.append()`, `paths.py` for session dir

**`handlers/simplify_trigger.py`** (NEW)

- PostToolUse handler with `Write` matcher
- If new file created during `code` phase → inject `/simplify` system message
- Reuses: `Hook.advanced_output({"systemMessage": ...})`

**`handlers/ci_check_handler.py`** (NEW)

- PostToolUse handler with `Skill` matcher
- After `/push` skill completes:
  - Poll CI via `gh pr checks <pr_number>`
  - Update `session.ci.status`
  - If fail and `iteration_count < ci_max_iterations`: trigger fix loop
  - If fail and max reached: set `session.ci.escalate_to_user = True`

**`handlers/cleanup_trigger.py`** (NEW)

- PostToolUse handler with `Skill` matcher
- After push + CI green: remove session worktree via `git worktree remove`

### 3.5 Run tests — all Phase 3 tests pass

---

## Phase 4: Settings and Frontmatter Wiring

### 4.1 `settings.local.json` Changes

**ADD to UserPromptSubmit:**

- `handlers/review_trigger.py`

**ADD to PreToolUse:**

- `guards/hold_checker.py` (matcher: `Agent`)
- `guards/hold_checker.py` (matcher: `Skill`)
- `guards/bash_guard.py` (matcher: `Bash`)

**ADD to PostToolUse:**

- `handlers/session_logger.py` (no matcher)
- `handlers/simplify_trigger.py` (matcher: `Write`)
- `handlers/ci_check_handler.py` (matcher: `Skill`)
- `handlers/cleanup_trigger.py` (matcher: `Skill`)

**REMOVE from PreToolUse:**

- `guards/phase_transition.py` entry (replaced by frontmatter `phase_guard.py`)

### 4.2 Skill Frontmatter — Phase Guards

Add `hooks:` YAML frontmatter to each command:

| Command File                      | Guard Args               | Exists?    |
| --------------------------------- | ------------------------ | ---------- |
| `.claude/commands/code.md`        | `pre-coding code`        | Yes        |
| `.claude/commands/code-review.md` | `code review`            | **CREATE** |
| `.claude/commands/commit.md`      | `review final-commit`    | Yes        |
| `.claude/commands/create-pr.md`   | `final-commit create-pr` | **CREATE** |
| `.claude/commands/validate.md`    | `create-pr validate`     | **CREATE** |
| `.claude/commands/push.md`        | `validate push`          | Yes        |

Frontmatter format:

```yaml
hooks:
  PreToolUse:
    - hooks:
        - type: command
          command: "python3 '$CLAUDE_PROJECT_DIR/.claude/hooks/workflow/guards/phase_guard.py' <predecessor> <current>"
          timeout: 10
```

### 4.3 Agent Frontmatter — Validation Hooks

**`.claude/agents/quality-assurance/code-reviewer.md`** (MODIFY)

- Currently has only `decision_guard.py` Stop hook
- Add `validation_loop.py` and `escalate.py`:

```yaml
hooks:
  Stop:
    - hooks:
        - type: command
          command: "python3 '$CLAUDE_PROJECT_DIR/.claude/hooks/workflow/validation/decision_guard.py'"
          timeout: 10
        - type: command
          command: "python3 '$CLAUDE_PROJECT_DIR/.claude/hooks/workflow/validation/validation_loop.py'"
          timeout: 10
        - type: command
          command: "python3 '$CLAUDE_PROJECT_DIR/.claude/hooks/workflow/validation/escalate.py'"
          timeout: 10
```

---

## Phase 5: Cleanup

- Delete `guards/phase_transition.py` (replaced by `guards/phase_guard.py`)
- Remove `plan_review copy.md` duplicate template
- Reset `state.json` to new multi-session structure
- Remove flat state keys from any remaining code

---

## File Summary

### New Files (8)

| File                                                  | Type    |
| ----------------------------------------------------- | ------- |
| `.claude/hooks/workflow/session_state.py`             | Core    |
| `.claude/hooks/workflow/guards/phase_guard.py`        | Guard   |
| `.claude/hooks/workflow/guards/hold_checker.py`       | Guard   |
| `.claude/hooks/workflow/guards/bash_guard.py`         | Guard   |
| `.claude/hooks/workflow/handlers/review_trigger.py`   | Handler |
| `.claude/hooks/workflow/handlers/session_logger.py`   | Handler |
| `.claude/hooks/workflow/handlers/simplify_trigger.py` | Handler |
| `.claude/hooks/workflow/handlers/ci_check_handler.py` | Handler |
| `.claude/hooks/workflow/handlers/cleanup_trigger.py`  | Handler |

### Modified Files (18)

| File                                                | Change                              |
| --------------------------------------------------- | ----------------------------------- |
| `config.yaml`                                       | Add ci_max_iterations, sessions_dir |
| `constants/phases.py`                               | Add status/CI constants             |
| `handlers/implement_trigger.py`                     | Multi-session creation              |
| `handlers/recorder.py`                              | Session-scoped recording            |
| `handlers/phase_recorder.py`                        | Session-scoped                      |
| `handlers/pr_recorder.py`                           | Session-scoped                      |
| `handlers/record_done.py`                           | Session-scoped                      |
| `guards/pre_coding_phase.py`                        | Session-scoped                      |
| `guards/code_phase.py`                              | Session-scoped                      |
| `guards/stop_guard.py`                              | Session-scoped + CI check           |
| `validation/decision_handler.py`                    | Session-scoped                      |
| `validation/decision_guard.py`                      | Session-scoped                      |
| `validation/validation_loop.py`                     | Session-scoped                      |
| `validation/escalate.py`                            | Session-scoped                      |
| `lib/launch-claude.py`                              | Set STORY_ID env var                |
| `initialize_state.py`                               | Multi-session init                  |
| `.claude/settings.local.json`                       | Add/remove hooks                    |
| `.claude/agents/quality-assurance/code-reviewer.md` | Add Stop hooks                      |

### New Commands (3)

| File                              | Purpose                   |
| --------------------------------- | ------------------------- |
| `.claude/commands/code-review.md` | Review phase command      |
| `.claude/commands/create-pr.md`   | PR creation phase command |
| `.claude/commands/validate.md`    | Validation phase command  |

### Deleted Files (1)

| File                         | Reason                       |
| ---------------------------- | ---------------------------- |
| `guards/phase_transition.py` | Replaced by `phase_guard.py` |

---

## TDD Approach

Each phase follows **Red → Green → Verify**:

- **Red**: Write failing tests FIRST in `tests/` using existing patterns (pytest, `helpers.py` factories, `conftest.py` fixtures)
- **Green**: Implement the minimum code to pass the tests
- **Verify**: Run `pytest .claude/hooks/workflow/tests/` after each phase to confirm all pass

### New test files

| Test File                     | Covers                                                                                                  |
| ----------------------------- | ------------------------------------------------------------------------------------------------------- |
| `tests/test_session_state.py` | Phase 1 — `SessionState` CRUD, defaults, env var                                                        |
| `tests/test_new_guards.py`    | Phase 3 — `phase_guard`, `hold_checker`, `bash_guard`                                                   |
| `tests/test_new_handlers.py`  | Phase 3 — `review_trigger`, `session_logger`, `simplify_trigger`, `ci_check_handler`, `cleanup_trigger` |

### Modified test files

| Test File                       | Changes                                           |
| ------------------------------- | ------------------------------------------------- |
| `tests/conftest.py`             | Add `mock_session_state`, `story_id_env` fixtures |
| `tests/test_guards.py`          | Update mocks from flat state to `SessionState`    |
| `tests/test_handlers.py`        | Update mocks from flat state to `SessionState`    |
| `tests/test_validation_loop.py` | Add `STORY_ID` env var to subprocess calls        |

### Test conventions (match existing patterns)

- Use `tmp_path` for state files, `monkeypatch.setenv` for `STORY_ID`
- Use `helpers.py` factories (`make_pre_tool_input`, etc.) for hook input
- Use `@patch` for module-level deps (`cfg`, `check_workflow_gate`)
- Assert exit codes: `pytest.raises(SystemExit)` with `exc.value.code == 2` for blocks
- Test no-op behavior when `STORY_ID` is absent

---

## Verification

1. **Run full test suite**: `cd .claude/hooks/workflow && pytest tests/ -v`
2. **Hook smoke tests**: `echo '{}' | STORY_ID=SK-TEST python3 hook.py` for each modified hook
3. **Integration**: Run `/implement SK-TEST` → verify session created in state.json under `sessions.SK-TEST`
4. **Parallel**: Launch 2 tmux sessions → verify both write to separate session keys without corruption
5. **Phase guard**: Verify `phase_guard.py pre-coding code` blocks when current phase is not `pre-coding`
6. **Graceful fallback**: Run hooks without `STORY_ID` env var → verify no crash, no-op behavior
