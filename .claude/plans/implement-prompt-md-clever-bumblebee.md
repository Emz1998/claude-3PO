# Revise Recorder to a narrow 19-method state API

## Context

`claude-3PO/scripts/utils/recorder.py` currently does three jobs mashed together: (1) dispatch for every `PostToolUse` event, (2) business logic (specs doc writing, PR/CI JSON parsing, plan-metadata injection, phase-skill handlers, file-write/edit routing), and (3) raw state mutation. This makes it hard to reason about and hard to call from meta-skills that want to declare "here's what I just did" without going through the tool-event dispatch.

The goal is to collapse the Recorder into a flat state-mutation API — 19 explicit methods, one per state concept — so skills (and any other code) can record state changes directly. The rich auto-extraction/dispatch logic is **removed**; callers must now call the new methods explicitly. All dispatchers are updated in the same change so the tree stays green.

## Key design decisions (confirmed with user)

1. Strip the class to exactly the 19 listed methods — delete dispatch, specs writing, PR/CI parsing, phase-skill handlers, plan metadata/section injection, created-task/subtask, phase-transition auto-complete, etc.
2. Update all callers + tests in the same change.
3. **All args on every method are optional**; only provided ones are written (partial-update semantics).
4. `record_workflow(type=None, active=None, status=None)` — three separate keyword args.
5. `record_command(command: str)` appends to new `state.commands: list[str]`.
6. `record_phase(name, status="in_progress")` — builds the dict internally, appends to `state.phases`.
7. `record_validation_result(result)` appends to new `state.validations: list[Validation]` (loop-style, like reviews).
8. New state fields: `test_mode`, `commands`, `report_file_path`, `validations`, `project_tasks: list[Task]`.
9. `TestReview` gains `iteration: int` and `status: ReviewResult | None`.

## Scope of deletions (what goes away)

Removed from Recorder (and no longer performed by hooks):

- `record_phase_transition` (incl. `_NO_TRANSITION_SKILLS`)
- `record_test_execution` (bash command regex → `tests.executed`)
- `record_pr_create`, `record_ci_check` (PR/CI JSON parsing)
- `record_write`, `record_plan_write`, `_record_specs_doc`, `record_plan_metadata`, `record_plan_sections`
- `record_edit` (code/test revision routing)
- `record_scores`, `record_verdict`, `record_revision_files`
- `write_specs_doc`, `_write_architecture`, `_write_backlog`, `mark_specs_agent_failed`
- `record_created_task`, `record_subtask` (replaced by `record_task`)
- `apply_phase_skill`, `_apply_continue`, `_apply_plan_approved`, `_apply_revise_plan`
- `record`, `_record_skill`, `_record_file_write`, `_record_bash`, `TOOL_RECORDERS`
- `_canonicalize_specs_path`, `_is_specs_phase_mismatch`, `_is_session_file`

**Consequence:** hooks no longer auto-record state on tool events. Meta-skills (or whatever code runs after tool events) must call the new methods explicitly. PR/CI status extraction from `gh` JSON, specs doc writing, and plan metadata injection are no longer the Recorder's job — this plan **deletes** them (not moves them). Callers that currently rely on those side-effects will lose that feature in this refactor.

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

### 3. Dispatchers — strip calls to removed methods

- `claude-3PO/scripts/dispatchers/post_tool_use.py:127` — remove `Recorder(state).record(hook_input, config)` entirely. Hook becomes: read stdin → `resolve(config, state)`. (Auto-recording on tool events disappears.)
- `claude-3PO/scripts/dispatchers/pre_tool_use.py:160` — delete the `Recorder(state).apply_phase_skill(...)` call and the block around it.
- `claude-3PO/scripts/dispatchers/post_tool_use_failure.py:61-62` — delete `record_test_execution` call.
- `claude-3PO/scripts/dispatchers/subagent_stop.py` — delete `mark_specs_agent_failed` (line 134), `write_specs_doc` / `record_scores` / `record_verdict` / `record_revision_files` (lines 219–225). Replace the review recording with direct `record_code_review` / `record_test_review` calls where the guard already exposes parsed scores/verdict; otherwise, delete. Specs doc writing and specs-agent-failure marking are dropped.
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

- `cd claude-3PO/scripts && pytest tests/` — full suite green, with `test_recorders.py` covering every new method (partial updates, list-op add vs replace, review append, task append with/without parent).
- `python -c "from utils.recorder import Recorder; print([m for m in dir(Recorder) if not m.startswith('_')])"` — output is exactly the 19 public methods.
- `python -c "from models.state import Task, Validation; print(Task.model_fields.keys(), Validation.model_fields.keys())"` — confirms new models.
- Manually wire one dispatcher (e.g. `task_created.py`) in a fresh workflow and confirm tasks land in `state.project_tasks` as `Task` dicts with/without `parent_task_id`.

## Risks & callouts

- **Feature loss (intentional):** PR/CI JSON parsing, specs-doc writing, plan-metadata injection, phase-skill lifecycle (`/continue`, `/plan-approved`, `/revise-plan`), auto phase-transition on Skill events, and implicit test-execution detection from bash commands are **gone** after this refactor. Downstream resolvers that assume these side-effects must be revisited separately.
- **`post_tool_use` hook becomes passive:** it will no longer mutate state based on tool events. Skills must explicitly call the new recorder methods to keep state in sync.
- **`project_tasks` shape change:** was `list[dict]`, becomes `list[Task]`. Any existing on-disk `state.jsonl` entries for active sessions will still load (pydantic `extra="allow"`), but field-level reads that used dict keys not present on `Task` may miss data — worth a quick grep of resolvers for `pt.get(...)` patterns before shipping. Scope of that audit is outside this plan.
