# Unified Guardrail Consolidation

## Context

The workflow guardrail system currently has 3 separate guardrail files: `guardrail.py` (dead code), `plan_guardrail.py` (plan workflow), and `coding_guardrail.py` (code workflow). The `implement.md` command specifies a full end-to-end workflow with features missing from the current implementation: task creation phase, test-run gate, CI pipeline gate, and report writing gate.

The user wants to consolidate everything into a single unified `guardrail.py` using modular `guards/` architecture, supporting both `/plan` (plan-only) and `/implement` (full plan+code) workflows.

## Approach

Rewrite `guardrail.py` as a unified guardrail that dispatches to modular guards. Replace `plan_guardrail.py` and `coding_guardrail.py` with a single entry point. Use a flat phase model instead of nested workflow namespaces. **TDD methodology**: write failing tests first for each guard, then implement.

### Agent Name Convention

- `PlanReview` (not `Plan-Review`)
- `TaskManager` (not `task-manager`)
- `TestReviewer`, `Validator`, `Explore`, `Research`, `Plan` (unchanged)

### Phase Flow

**`/implement` workflow:**
```
explore → plan → write-plan → review → approved → task-create → write-tests → write-code → validate → pr-create → ci-check → report → completed
```

**`/plan` workflow (subset):**
```
explore → plan → write-plan → review → approved
```

TDD=false skips `write-tests` (goes straight to `write-code`).
No story ID skips `task-create`.
Skip flags skip `explore`/`research` agents.

### Unified State Model

Single flat state in `state.json` — minimal nesting, only group related fields:
```json
{
  "workflow_active": true,
  "workflow_type": "plan|implement",
  "phase": "explore|plan|write-plan|review|approved|task-create|write-tests|write-code|validate|pr-create|ci-check|report|completed|failed",
  "tdd": true,
  "story_id": null,
  "skip_explore": false,
  "skip_research": false,
  "instructions": "",
  "agents": [{ "agent_type": "Explore", "status": "running|completed", "tool_use_id": "" }],
  "plan_file": null,
  "plan_written": false,
  "plan_review_iteration": 0,
  "plan_review_scores": null,
  "plan_review_status": null,
  "tasks_created": 0,
  "test_files_created": [],
  "test_review_result": null,
  "test_run_executed": false,
  "validation_result": null,
  "pr_status": "pending",
  "ci_status": "pending",
  "ci_check_executed": false,
  "report_written": false
}
```

## Steps

> **TDD approach**: For each guard module, write failing tests first, then implement the guard to pass them.

### Step 1: Write tests + implement guard modules (TDD)

For each guard, create `tests/test_<guard>.py` first with failing tests, then implement the guard.

#### 1a. `guards/skill_guard.py` + `tests/test_skill_guard.py`

**Test first**, then implement:
- Intercepts `/plan` and `/implement` skill invocations (PostToolUse of Skill + UserPromptSubmit)
- Activates workflow: sets `workflow_active`, `workflow_type`, parses skip flags, sets initial phase
- `/implement` → `workflow_type: "implement"`, `/plan` → `workflow_type: "plan"`
- Non-matching skills return `("allow", "")`

#### 1b. `guards/agent_guard.py` + `tests/test_agent_guard.py`

**Test first**, then rewrite:
- Phase-based agent validation using flat state:
  - `explore`: Explore (max 3), Research (max 2). Block background execution.
  - `plan`: Plan (max 1)
  - `review`: PlanReview (max 3). Requires `plan_written == true`.
  - `task-create`: TaskManager (max 1)
  - `write-tests`: TestReviewer. Requires test files created.
  - `write-code`: Validator (triggers `validate` phase transition)
  - `validate`: Validator only
  - All other phases: block agents
- Records agent in `agents[]` on allow

#### 1c. `guards/read_guard.py` + `tests/test_read_guard.py`

**Test first**, then create:
- Only enforced during coding phases (`write-tests`, `write-code`, `validate`, `ci-check`, `report`) — NOT during explore/plan/review phases
- Extracts the plan's file list from state (`plan_file` path → parse "Files to Modify" or "Critical Files" section)
- **PreToolUse** Read: If file is not in the plan's file list and not a `.claude/` config file and not a test file (during write-tests), block with reason "File not listed in plan"
- Allows `.claude/` paths, `node_modules/`, `package.json`, config files (non-code files) always
- Caches parsed plan file list in state to avoid re-parsing on every Read call

#### 1d. `guards/write_guard.py` + `tests/test_write_guard.py`

**Test first**, then rewrite:
- **PreToolUse** (`validate_pre`): Phase-based file write blocking
  - `write-plan`/`review`: Only `.claude/plans/` allowed for code files
  - `write-tests`: Only test files allowed (code files blocked)
  - `write-code`: Code files allowed
  - `ci-check`: Code files allowed, but writing triggers phase regression to `write-code` (must re-validate + re-PR + re-CI)
  - `validate`/`pr-create`: Code files blocked
  - `report`: Only `.claude/reports/` allowed
  - Non-code files and `.claude/` config files always allowed
- **PostToolUse** (`handle_post`): Track plan writes (set `plan_written`, `plan_file`, advance to `review`), track test files created, track report writes
- **Report archiving**: When a write to `.claude/reports/latest-report.md` is detected in PostToolUse, the guard automatically archives any existing `latest-report.md` to `.claude/reports/archive/<timestamp>-report.md` before allowing the write. Sets `report_written = true` and advances phase to `completed`.

#### 1e. `guards/bash_guard.py` + `tests/test_bash_guard.py`

**Test first**, then rewrite:
- **PreToolUse** (`validate_pre`): Block PR commands (`gh pr create`, `git push`) outside `pr-create` phase. Block if validation not passed.
- **PostToolUse** (`handle_post`):
  - Track test-run commands (`pytest`, `npm test`, `yarn test`, `go test`, `jest`, `vitest`) → set `test_run_executed = true`
  - Track PR creation → advance to `ci-check`
  - Track CI check commands (`gh pr checks`, `gh run view`) → set `ci_check_executed = true`, set `ci_status` to `"passed"` or `"failed"` based on output parsing (look for "All checks were successful" / "Some checks were not successful")
  - **CI pass**: `ci_status = "passed"` → advance to `report`
  - **CI failure iteration**: `ci_status = "failed"` → keep phase as `ci-check`. Write/Edit to code files triggers phase regression to `write-code`, resets `ci_status = "pending"`, `ci_check_executed = false`, `validation_result = null`, `pr_status = "pending"`. Agent must re-run: Validator → PR create → CI check

#### 1f. `guards/review_guard.py` + `tests/test_review_guard.py`

**Test first**, then rewrite. SubagentStop handler for all agent types:
- Explore/Research: Mark completed, auto-advance to `plan` when all required agents done
- Plan: Advance to `write-plan`
- PlanReview: Parse confidence/quality scores (reuse `parse_scores`), advance to `approved` or iterate (max 3)
- TaskManager: Advance to `write-tests`/`write-code` depending on `tdd` flag
- TestReviewer: Parse Pass/Fail verdict, advance to `write-code` or keep in `write-tests`
- Validator: Parse Pass/Fail verdict, advance to `pr-create` or return to `write-code`

#### 1g. `guards/stop_guard.py` + `tests/test_stop_guard.py`

**Test first**, then rewrite:
- `/plan` workflow: Allow stop after `approved` phase
- `/implement` workflow: Block unless `phase == "completed"`. Collect reasons: tests failing, validation not passed, PR not created, CI not checked, report not written.
- `stop_hook_active` bypass (re-entry guard)

#### 1h. `guards/webfetch_guard.py` + `tests/test_webfetch_guard.py`

**Test first**, then create:
- Domain whitelist validation (extracted from plan_guardrail.py SAFE_DOMAINS list)
- Only enforced when `workflow_active == true`

#### 1i. `guards/task_guard.py` + `tests/test_task_guard.py`

**Test first**, then create:
- Handles `TaskCreated` hook event (has `task_id`, `task_subject`, `task_description` directly in payload)
- During `task-create` phase: validates task subject matches project task format (e.g., prefixed with story ID)
- Blocks task creation (exit code 2 style deny) if subject format is invalid
- Tracks created tasks count in state
- Replaces the old `task_recorder.py` + `task_list_recorder.py` + `task_validator.py` pipeline

### Step 2: Write tests + implement guardrail.py (TDD)

Create `tests/test_guardrail.py` with integration tests first, then rewrite `guardrail.py`:

```python
def _dispatch(hook_input, state_path):
    store = StateStore(state_path)
    event = hook_input["hook_event_name"]
    tool = hook_input.get("tool_name", "")

    if event == "PreToolUse":
        if tool == "Agent": return agent_guard.validate(hook_input, store)
        if tool == "Read": return read_guard.validate(hook_input, store)
        if tool in ("Write", "Edit"): return write_guard.validate_pre(hook_input, store)
        if tool == "Bash": return bash_guard.validate_pre(hook_input, store)
        if tool == "WebFetch": return webfetch_guard.validate(hook_input, store)
        if tool == "ExitPlanMode": return _handle_exit_plan_mode(hook_input, store)

    if event == "PostToolUse":
        if tool == "Skill": return skill_guard.handle(hook_input, store)
        if tool in ("Write", "Edit"): return write_guard.handle_post(hook_input, store)
        if tool == "Bash": return bash_guard.handle_post(hook_input, store)
        if tool == "ExitPlanMode": return _handle_post_exit_plan_mode(hook_input, store)

    if event == "TaskCreated": return task_guard.validate(hook_input, store)
    if event == "SubagentStop": return review_guard.handle(hook_input, store)
    if event == "Stop": return stop_guard.validate(hook_input, store)
    if event == "UserPromptSubmit": return skill_guard.handle(hook_input, store)

    return "allow", ""
```

Key `ExitPlanMode` handling (in guardrail.py, not a guard):
- **PreToolUse**: Validate plan is written, review is approved, template is valid. Return plan content as `additionalContext`.
- **PostToolUse**: For `/implement`, advance phase to `task-create` (or `write-tests`/`write-code` if no story). For `/plan`, workflow ends at `approved`.

### Step 3: Create unified dispatchers

Replace `dispatchers/plan_guardrail/` and `dispatchers/coding_guardrail/` with unified dispatchers:

- `dispatchers/pre_tool_use.py` — Routes to guardrail.py
- `dispatchers/post_tool_use.py` — Routes to guardrail.py
- `dispatchers/subagent_stop.py` — Routes to guardrail.py
- `dispatchers/stop.py` — Routes to guardrail.py
- `dispatchers/task_created.py` — Routes to guardrail.py
- `dispatchers/user_prompt_submit.py` — Routes to guardrail.py

### Step 4: Update settings.local.json

Replace all hook registrations with unified dispatchers:

```json
{
  "hooks": {
    "PreToolUse": [{
      "hooks": [{ "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/workflow/dispatchers/pre_tool_use.py", "timeout": 30 }]
    }],
    "PostToolUse": [{
      "hooks": [{ "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/workflow/dispatchers/post_tool_use.py", "timeout": 30 }]
    }],
    "SubagentStop": [{
      "hooks": [{ "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/workflow/dispatchers/subagent_stop.py", "timeout": 30 }]
    }],
    "UserPromptSubmit": [{
      "hooks": [{ "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/workflow/dispatchers/user_prompt_submit.py", "timeout": 30 }]
    }],
    "TaskCreated": [{
      "hooks": [{ "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/workflow/dispatchers/task_created.py", "timeout": 30 }]
    }],
    "Stop": [{
      "hooks": [{ "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/workflow/dispatchers/stop.py", "timeout": 30 }]
    }]
  }
}
```

No matchers needed — the guardrail's `_dispatch` returns `("allow", "")` for unhandled tools, so all events are routed through the unified guardrail safely.

### Step 5: Delete obsolete files

- `plan_guardrail.py` — replaced by unified guardrail.py
- `coding_guardrail.py` — replaced by unified guardrail.py
- `dispatchers/plan_guardrail/` — replaced by unified dispatchers
- `dispatchers/coding_guardrail/` — replaced by unified dispatchers
- `dispatchers/full_guardrail/` — dead code
- `dry_runs/full_dry_run.py` — dead code
- `tests/test_plan_guardrail.py` — replaced by new guard-level tests
- `tests/test_coding_guardrail.py` — replaced by new guard-level tests
- `tests/test_guardrail.py` (old) — replaced by new integration tests

### Step 6: Create dry runs

Two dry runs only:

- `dry_runs/plan_dry_run.py` — Simulates `/plan` workflow end-to-end against unified guardrail.py: skill activation → explore agents → plan agent → write plan → PlanReview → ExitPlanMode
- `dry_runs/implement_dry_run.py` — Simulates `/implement` workflow end-to-end (replaces `coding_dry_run.py`): full plan phase + task-create → write-tests (TDD) → TestReviewer → write-code → test-run → Validator → pr-create → ci-check → report → completed

## Files to Modify

### Guards (TDD: test first, then implement)
| File | Action |
|------|--------|
| `guards/skill_guard.py` | **Create** |
| `guards/agent_guard.py` | **Rewrite** |
| `guards/read_guard.py` | **Create** — plan-scoped file access |
| `guards/write_guard.py` | **Rewrite** |
| `guards/bash_guard.py` | **Rewrite** |
| `guards/review_guard.py` | **Rewrite** |
| `guards/stop_guard.py` | **Rewrite** |
| `guards/webfetch_guard.py` | **Create** |
| `guards/task_guard.py` | **Create** — TaskCreated validation |
| `tests/test_skill_guard.py` | **Create** |
| `tests/test_agent_guard.py` | **Create** |
| `tests/test_read_guard.py` | **Create** |
| `tests/test_write_guard.py` | **Create** |
| `tests/test_bash_guard.py` | **Create** |
| `tests/test_review_guard.py` | **Create** |
| `tests/test_stop_guard.py` | **Create** |
| `tests/test_webfetch_guard.py` | **Create** |
| `tests/test_task_guard.py` | **Create** |

### Core (TDD: test first, then implement)
| File | Action |
|------|--------|
| `guardrail.py` | **Rewrite** — unified dispatcher |
| `tests/test_guardrail.py` | **Rewrite** — integration tests |

### Dispatchers
| File | Action |
|------|--------|
| `dispatchers/pre_tool_use.py` | **Rewrite** — unified routing |
| `dispatchers/post_tool_use.py` | **Rewrite** — unified routing |
| `dispatchers/subagent_stop.py` | **Rewrite** — unified routing |
| `dispatchers/stop.py` | **Create** |
| `dispatchers/task_created.py` | **Create** |
| `dispatchers/user_prompt_submit.py` | **Create** |

### Config
| File | Action |
|------|--------|
| `.claude/settings.local.json` | **Edit** — replace hook registrations |

### Delete
| File | Action |
|------|--------|
| `plan_guardrail.py` | **Delete** |
| `coding_guardrail.py` | **Delete** |
| `dispatchers/plan_guardrail/` | **Delete** directory |
| `dispatchers/coding_guardrail/` | **Delete** directory |
| `dispatchers/full_guardrail/` | **Delete** directory |
| `dispatchers/tasks.py` | **Delete** |
| `dry_runs/full_dry_run.py` | **Delete** |
| `dry_runs/coding_dry_run.py` | **Delete** (replaced by implement_dry_run.py) |
| `tests/test_plan_guardrail.py` | **Delete** |
| `tests/test_coding_guardrail.py` | **Delete** |
| `tests/test_task_guardrail.py` | **Delete** (replaced by test_task_guard.py) |
| `guards/task_recorder.py` | **Delete** (replaced by task_guard.py) |
| `guards/task_list_recorder.py` | **Delete** (replaced by task_guard.py) |
| `guards/task_validator.py` | **Delete** (replaced by task_guard.py) |

### Dry Runs
| File | Action |
|------|--------|
| `dry_runs/plan_dry_run.py` | **Rewrite** — `/plan` workflow |
| `dry_runs/implement_dry_run.py` | **Create** — `/implement` workflow |

### Keep (no changes)
| File | Reason |
|------|--------|
| `state_store.py` | Shared state persistence |
| `hook.py` | Shared hook I/O utilities |
| `session_state.py` | Session state wrapper |
| `tests/test_state_store.py` | Still valid |
| `tests/test_file_manager.py` | Still valid |

> All paths above are relative to `.claude/hooks/workflow/`

## Verification

1. **Unit tests**: `pytest .claude/hooks/workflow/tests/ -v` — all guard modules tested individually (TDD: tests written first)
2. **Dry runs**: `python3 .claude/hooks/workflow/dry_runs/plan_dry_run.py` (plan-only) and `python3 .claude/hooks/workflow/dry_runs/implement_dry_run.py --tdd` (full implement)
3. **Manual smoke test**: Invoke `/plan --skip-all test task` — verify guardrail activates, blocks out-of-order agents, allows plan write, validates template on ExitPlanMode
4. **State inspection**: After dry runs, verify `state.json` reflects correct final state
