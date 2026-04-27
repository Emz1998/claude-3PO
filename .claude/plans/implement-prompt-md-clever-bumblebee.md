# Revise Recorder to a narrow 19-method state API

## Context

`claude-3PO/scripts/utils/recorder.py` currently does three jobs mashed together: (1) dispatch for every `PostToolUse` event, (2) business logic (specs doc writing, PR/CI JSON parsing, plan-metadata injection, phase-skill handlers, file-write/edit routing), and (3) raw state mutation. This makes it hard to reason about and hard to call from meta-skills that want to declare "here's what I just did" without going through the tool-event dispatch.

The goal is to collapse the Recorder's public surface into a flat state-mutation API — 19 explicit methods, one per state concept — so skills (and any other code) can record state changes directly. A thin `record(hook_input, config)` facade stays on the class so `post_tool_use.py` continues to call one entry point; internally it dispatches Skill/Write/Edit/Bash events onto the 19 new methods only. Anything that can't be expressed via those 19 methods (PR/CI JSON parsing, specs-doc writing, plan-metadata injection, phase-skill handlers) is **dropped**. All callers + tests are updated in the same change.

## Key design decisions (confirmed with user)

1. Strip the public API to exactly the 19 listed methods. Keep `record(hook_input, config)` as a **thin facade** (not counted toward the 19) that only maps tool events to those 19 methods.
2. Delete dispatch-era helpers that don't map: specs writing, PR/CI parsing, phase-skill handlers (`/continue`, `/plan-approved`, `/revise-plan`), plan metadata/section injection, created-task/subtask, phase-transition auto-complete.
3. Update all callers + tests in the same change.
4. **All args on every method are optional**; only provided ones are written (partial-update semantics).
5. `record_workflow(type=None, active=None, status=None)` — three separate keyword args.
6. `record_command(command: str)` appends to new `state.commands: list[str]`.
7. `record_phase(name, status="in_progress")` — builds the dict internally, appends to `state.phases`.
8. `record_validation_result(result)` appends to new `state.validations: list[Validation]` (loop-style, like reviews).
9. New state fields: `test_mode`, `commands`, `report_file_path`, `validations`, `project_tasks: list[Task]`.
10. `TestReview` gains `iteration: int` and `status: ReviewResult | None`.

## Scope of deletions (what goes away)

Removed outright (no replacement anywhere):

- `record_phase_transition` (incl. `_NO_TRANSITION_SKILLS`) — the facade now does a simple append via `record_phase`, no auto-complete-previous
- `record_test_execution` (bash command regex → `tests.executed`) — skills that run tests must call `record_tests(executed=True)` themselves
- `record_pr_create`, `record_ci_check` (PR/CI JSON parsing)
- `record_plan_metadata`, `record_plan_sections` (inject_plan_metadata / extract_plan_tasks side-effects)
- `record_scores`, `record_verdict`, `record_revision_files` (AgentReportGuard post-allow side-effects)
- `write_specs_doc`, `_write_architecture`, `_write_backlog`, `mark_specs_agent_failed`
- `record_created_task`, `record_subtask` (replaced by `record_task`)
- `apply_phase_skill`, `_apply_continue`, `_apply_plan_approved`, `_apply_revise_plan`
- `_canonicalize_specs_path`, `_is_specs_phase_mismatch`, `_is_session_file`

Reshaped (internal to the facade, not exposed as public methods):

- `record_write`, `record_edit` → internal routers inside `record()` that call the new `record_plan` / `record_tests` / `record_code_files` / `record_report_written` methods. They no longer touch specs paths.
- `_record_skill`, `_record_file_write`, `_record_bash`, `TOOL_RECORDERS` → retained as **private** dispatch plumbing underneath `record()`, but they only call the 19 new methods. No PR/CI, specs, or phase-skill branches remain.

**Consequence:** PR/CI status extraction from `gh` JSON, specs doc writing, plan metadata injection, implicit test-execution detection from bash commands, and phase-skill handlers (`/continue`, `/plan-approved`, `/revise-plan`) are **deleted**. Callers that currently rely on those side-effects will lose that feature in this refactor.

---

## Files to modify

### 1. `claude-3PO/scripts/models/state.py`

Add/update:

```python
class Task(_Base):
    task_id: str
    subject: str
    description: str | None = None
    parent_task_id: str | None = None

class Validation(_Base):
    result: Literal["pass", "fail"]

class TestReview(_Base):
    iteration: int = 0
    verdict: ReviewResult | None = None
    status: ReviewResult | None = None

class State(_Base):
    # ...existing fields...
    test_mode: str | None = None
    commands: list[str] = []
    report_file_path: str | None = None
    validations: list[Validation] = []
    project_tasks: list[Task] = []   # was: list[dict]
    # `tasks: list[str]` stays (plan-derived subjects) — untouched
```

### 2. `claude-3PO/scripts/utils/recorder.py` — full rewrite

Signature-only sketch (all arg-optional, partial update; each method ≤15 lines):

```python
ListOp = tuple[Literal["add", "replace"], list[str]]

class Recorder:
    def __init__(self, state: StateStore) -> None: ...

    # Artifacts
    def record_plan(self, file_path=None, written=None, revised=None, reviews=None) -> None
    def record_tests(self, file_paths: ListOp | None = None, executed=None,
                     reviews=None, files_to_revise: ListOp | None = None,
                     files_revised: ListOp | None = None) -> None
    def record_code_files(self, file_paths: ListOp | None = None, reviews=None,
                          files_to_revise: ListOp | None = None,
                          files_revised: ListOp | None = None) -> None
    def record_report_written(self, file_path: str | None = None, written: bool | None = None) -> None

    # Session / workflow metadata
    def record_command(self, command: str) -> None                # appends to state.commands
    def record_session_id(self, session_id: str) -> None
    def record_story_id(self, story_id: str) -> None
    def record_workflow_type(self, workflow_type: str) -> None
    def record_workflow_active(self, active: bool) -> None
    def record_workflow_status(self, status: Literal["in_progress","completed"]) -> None
    def record_workflow(self, type=None, active=None, status=None) -> None  # convenience

    # Lifecycle / flags
    def record_test_mode(self, test_mode: str) -> None
    def record_phase(self, name: str,
                     status: Literal["in_progress","completed","skipped"] = "in_progress") -> None
    def record_tdd(self, tdd: bool) -> None
    def record_validation_result(self, result: Literal["pass","fail"]) -> None  # append to validations

    # Agents / reviews / tasks
    def record_agent(self, name: str,
                     status: Literal["in_progress","completed","failed"],
                     tool_use_id: str) -> None
    def record_code_review(self, iteration: int, scores: dict,
                           status: ReviewResult | None = None) -> None
    def record_test_review(self, iteration: int, verdict: ReviewResult,
                           status: ReviewResult | None = None) -> None
    def record_task(self, task_id: str, subject: str, description: str,
                    parent_task_id: str | None = None) -> None
```

Implementation pattern (every method): one small `_apply(d: dict)` closure passed to `self.state.update(...)`; `ListOp=("add", xs)` extends + dedups; `ListOp=("replace", xs)` overwrites. Each method ≤15 lines with full Google-style docstring (context, Args, Returns, Raises, Example).

Plus the preserved facade (not counted toward the 19):

```python
class Recorder:
    # ...the 19 methods above...

    def record(self, hook_input: dict, config: Config) -> None:
        """Thin dispatch from a PostToolUse event to the new 19-method API.

        Skill -> record_phase, Write/Edit -> record_plan/tests/code_files/report_written,
        Bash -> record_command. Unknown tools are ignored. No PR/CI, specs,
        plan-metadata, or phase-skill side-effects.
        """
        handler = self._TOOL_RECORDERS.get(hook_input.get("tool_name", ""))
        if handler:
            handler(self, hook_input, config)
```

Private helpers (`_dispatch_skill`, `_dispatch_write`, `_dispatch_edit`, `_dispatch_bash`, `_TOOL_RECORDERS`) live on the class but are underscored so they don't count as public surface; each one decides which of the 19 methods to call based on the current phase and the tool payload. Keep each ≤15 lines.

### 3. Dispatchers — strip calls to removed methods

- `claude-3PO/scripts/dispatchers/post_tool_use.py:127` — **unchanged** call signature. `Recorder(state).record(hook_input, config)` keeps working via the thinned facade.
- `claude-3PO/scripts/dispatchers/pre_tool_use.py:160` — delete the `Recorder(state).apply_phase_skill(...)` call and the block around it.
- `claude-3PO/scripts/dispatchers/post_tool_use_failure.py:61-62` — delete `record_test_execution` call (auto-detection from bash command is gone).
- `claude-3PO/scripts/dispatchers/subagent_stop.py` — delete `mark_specs_agent_failed` (line 134), `write_specs_doc` / `record_scores` / `record_verdict` / `record_revision_files` (lines 219–225). Replace review recording with direct `record_code_review` / `record_test_review` calls where the guard already exposes parsed scores/verdict; otherwise delete. Specs doc writing and specs-agent-failure marking are dropped.
- `claude-3PO/scripts/dispatchers/task_created.py:99-103` — migrate to `record_task(task_id, subject, description, parent_task_id=...)`. Top-level task: no parent. Subtask: parent_task_id set.

### 4. Tests

- `claude-3PO/scripts/tests/test_recorders.py` — rewrite per-method tests for the 19-method surface. Keep the state-setter-based assertions (they read through `StateStore`).
- `claude-3PO/scripts/tests/test_recorder_dispatch.py` — **delete** (dispatch no longer exists).
- `claude-3PO/scripts/tests/test_specs_recorder.py` — **delete** (specs recording no longer exists).
- `claude-3PO/scripts/tests/helpers.py` — drop any helper exclusive to removed methods (`make_hook_input` may still be used by other tests; inspect and prune selectively).

### 5. Other touches

- `claude-3PO/scripts/lib/state_store.py` — no schema-change required for the property getters (pydantic `extra="allow"` covers the new fields). Optional: add thin property getters for `commands`, `validations`, `test_mode`, `report_file_path`, `project_tasks` so resolvers can read them idiomatically. Recorder writes directly via `update()` and does not depend on these additions.

## TDD order

1. Write the new `test_recorders.py` against the 19-method spec (all tests red).
2. Update `models/state.py` (new fields/models) → tests still red.
3. Rewrite `utils/recorder.py` → recorder tests green.
4. Delete `test_recorder_dispatch.py`, `test_specs_recorder.py`; prune `helpers.py`.
5. Update the five dispatcher files → full test suite green.

## Verification

- `cd claude-3PO/scripts && pytest tests/` — full suite green, with `test_recorders.py` covering every new method (partial updates, list-op add vs replace, review append, task append with/without parent) plus a thin-facade test that drives `record()` with a mocked Skill/Write/Edit/Bash payload and asserts the corresponding flat method was invoked.
- `python -c "from utils.recorder import Recorder; print(sorted(m for m in dir(Recorder) if not m.startswith('_') and m != 'record'))"` — output is exactly the 19 public `record_*` methods; `record` is the only extra public name.
- `python -c "from models.state import Task, Validation; print(Task.model_fields.keys(), Validation.model_fields.keys())"` — confirms new models.
- Manually wire one dispatcher (e.g. `task_created.py`) in a fresh workflow and confirm tasks land in `state.project_tasks` as `Task` dicts with/without `parent_task_id`.

## Risks & callouts

- **Feature loss (intentional):** PR/CI JSON parsing, specs-doc writing, plan-metadata injection, phase-skill lifecycle (`/continue`, `/plan-approved`, `/revise-plan`), and implicit test-execution detection from bash commands are **gone** after this refactor. Downstream resolvers that assume these side-effects must be revisited separately.
- **Facade semantics shift:** `record()` still exists and is still the `post_tool_use` entry point, but its behavior is strictly narrower — it only routes events that map to the 19 new methods. Hooks for phase-skills (`/continue`, `/plan-approved`, `/revise-plan`) no longer have any state effect via this pathway.
- **`project_tasks` shape change:** was `list[dict]`, becomes `list[Task]`. Any existing on-disk `state.jsonl` entries for active sessions will still load (pydantic `extra="allow"`), but field-level reads that used dict keys not present on `Task` may miss data — worth a quick grep of resolvers for `pt.get(...)` patterns before shipping. Scope of that audit is outside this plan.
