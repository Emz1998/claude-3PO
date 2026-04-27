---
name: test-implement
description: Live E2E test of implement workflow guardrails
allowed-tools: Bash, Read, Glob, Grep, Write, Edit, Agent, WebFetch
model: haiku
---

You are a **guardrail test runner** for the **implement workflow**. Systematically test every guardrail by deliberately doing wrong things first (which MUST be blocked), then doing the correct thing to advance.

## Workflow Initialization

!`python3 '${CLAUDE_PLUGIN_ROOT}/scripts/utils/initializer.py' implement ${CLAUDE_SESSION_ID} --tdd --test SK-TEST`

## Rules

- When you get blocked, that is the **expected** outcome. Record it as PASS.
- If a step marked "should block" is NOT blocked, record it as FAIL.
- All subagents must exit immediately — no real work. Every agent prompt: "Do not read any files. Respond with exactly: ..." followed by the required output format.
- After each phase transition, read `state.jsonl` for your session and verify the state matches expectations. Record state mismatches as FAIL.
- Write results to `.claude/reports/E2E_TEST_REPORT.md` after each phase. This file is always writable in test mode.
- The state file is at: `'${CLAUDE_PLUGIN_ROOT}/scripts/state.jsonl'`
- The violations log is at: `.claude/logs/violations.md`

## Report Format

Present two tables at the end:

**Guardrail Tests:**

```
| Phase | Step | Expected | Actual | Result |
|-------|------|----------|--------|--------|
```

**State Verification:**

```
| Phase | Check | Expected | Actual | Result |
|-------|-------|----------|--------|--------|
```

---

## Phase: explore + research

Invoke `/explore` and `/research` in parallel (both skills in the same message).

1. `Write` to `test-guardrail.py` — _should block_ (read-only phase)
2. `Agent` with `subagent_type: "Plan"` — _should block_ (wrong agent for explore)
3. `Bash` with `ls -la` — _should allow_
4. `Agent` with `subagent_type: "Explore"`, prompt: "Respond with exactly: Done." — _should allow_
5. Invoke 2 more Explore agents (total 3) with same prompt — _should allow_
6. `Agent` with `subagent_type: "Research"`, prompt: "Respond with exactly: Done." — _should allow_
7. Invoke 1 more Research agent (total 2) with same prompt — _should allow_
8. Wait for all agents to complete

**State check:** Verify:

- `phases` has explore (completed) and research (completed)
- `agents` has 3 Explore + 2 Research, all "completed"
- `workflow_type` is `"implement"`

## Phase: plan (implement template)

1. Invoke `/plan`
2. `Agent` with `subagent_type: "Plan"`, prompt: "Respond with exactly: Done." — _should allow_
3. `Write` to `.claude/plans/latest-plan.md` with content below — _should block_ (implement requires Context, Approach, Files to Create/Modify, Verification)

```markdown
# Plan

## Dependencies
- flask

## Tasks
- Build login

## Files to Modify

| Action | Path |
|--------|------|
| Create | src/app.py |
```

4. `Write` to `.claude/plans/latest-plan.md` with content below — _should block_ (missing Context)

```markdown
# Plan

## Approach
Do stuff.

## Files to Create/Modify

| Action | Path |
|--------|------|
| Create | src/app.py |

## Verification
Test it.
```

5. `Write` to `.claude/plans/latest-plan.md` with content below — _should block_ (missing Files to Create/Modify)

```markdown
# Plan

## Context
Some context.

## Approach
Do stuff.

## Verification
Test it.
```
6. `Write` to `.claude/plans/latest-plan.md` with valid content below — _should allow_

```
# Test Plan

## Context
Testing implement guardrails.

## Approach
Create a hello function in src/hello.py.

## Files to Create/Modify

| Action | Path |
|--------|------|
| Create | src/hello.py |
| Create | src/utils.py |

## Verification

Run pytest.
```

**State check:** Verify:

- `plan.written` is `true`
- `plan.file_path` is `.claude/plans/latest-plan.md`

## Phase: plan-review

1. Invoke `/plan-review`
2. `Edit` on `wrong.md` — _should block_ (only plan file editable)
3. `Edit` on `.claude/plans/latest-plan.md`, old*string: "Testing implement guardrails", new_string: "Testing implement workflow guardrails" — \_should allow*
4. `Agent` with `subagent_type: "PlanReview"`, prompt below — _should allow_

```
Do not read any files. Respond with exactly:

Confidence Score: 95
Quality Score: 95
```

**State check:** Verify:

- `plan.reviews` has 1 entry with `status: "Pass"`
- `plan-review` status is `completed`

### /revise-plan happy path

5. `/revise-plan improve the approach` — _should allow_ (reopens plan-review)

**State check:** Verify `plan-review` status is `in_progress`, `plan.revised` is `false`

6. `Agent` with `subagent_type: "PlanReview"` — _should block_ (must edit plan first)
7. `Edit` on `.claude/plans/latest-plan.md`, old_string: "Testing implement workflow guardrails", new_string: "Testing implement workflow guardrails — revised" — _should allow_
8. `Agent` with `subagent_type: "PlanReview"`, prompt below — _should allow_

```
Do not read any files. Respond with exactly:

Confidence Score: 95
Quality Score: 95
```

### /continue and /revise-plan edge cases

9. `/continue` — _should allow_ (resume after checkpoint)

**State check:** Verify `plan-review` status is `completed`

10. `/continue` — _should block_ (current phase is now create-tasks, not a review phase)
11. `/revise-plan more changes` — _should block_ (current phase is create-tasks, not plan-review)

## Phase: create-tasks (AUTO)

Auto-starts after plan-review.

1. `/create-tasks` — _should block_ (auto-phase)
2. `TaskCreate` with subject: "Write form", description: "Do it" (no metadata) — _should block_ (missing parent_task_id)
3. `TaskCreate` with subject: "Write form", description: "Do it", metadata: {parent*task_id: "T-999", parent_task_title: "Ghost"} — \_should block* (T-999 not in project tasks)
4. `TaskCreate` with subject: "Write form", description: "Do it", metadata: {parent*task_id: "T-001"} — \_should block* (missing parent_task_title)
5. `TaskCreate` with subject: "", description: "Something", metadata: {parent*task_id: "T-001", parent_task_title: "Build login"} — \_should block* (empty subject)
6. `TaskCreate` with subject: "Write form", description: "", metadata: {parent*task_id: "T-001", parent_task_title: "Build login"} — \_should block* (empty description)

**Note:** Steps 2-6 require project tasks in state. If no project tasks are loaded (SK-TEST has no real data), note these as skipped.

7. If project tasks are available: `TaskCreate` with valid metadata — _should allow_

**State check:** If tasks were created, verify:

- `project_tasks[].subtasks` has the child task with `status: "in_progress"`

## Phase: write-tests (AUTO, TDD)

1. `/write-tests` — _should block_ (auto-phase)
2. `Write` to `app.py` — _should block_ (test files only)
3. `Write` to `test_hello.py` with content:

```python
def test_hello():
    from hello import hello
    assert hello() is None
```

— _should allow_ 4. `Bash` with `python -m pytest test_hello.py -v` — _should allow_

**State check:** Verify:

- `tests.file_paths` contains `["test_hello.py"]`
- `tests.executed` is `true`

## Phase: tests-review

1. Invoke `/tests-review`
2. `Edit` on `unknown.py` — _should block_ (not a test file in session)
3. `Edit` on `test_hello.py`, old*string: `assert hello() is None`, new_string: `assert hello() is None  # verified` — \_should allow*
4. `Agent` with `subagent_type: "TestReviewer"`, prompt below — _should allow_

```
Do not read any files. Respond with exactly:

## Files to revise
- test_hello.py

Pass
```

**State check:** Verify:

- `tests.reviews` has 1 entry with `verdict: "Pass"`
- `tests-review` status is `completed`

## Phase: write-code (AUTO — implement file guard)

Auto-starts after tests-review passes.

1. `/write-code` — _should block_ (auto-phase)
2. `Write` to `src/other.py` with content `x = 1` — _should block_ (not in Files to Create/Modify)
3. `Write` to `readme.md` — _should block_ (not in Files to Create/Modify)
4. `Write` to `src/hello.py` with content below — _should allow_ (listed)

```python
def hello(): return "hello"
```
5. `Write` to `src/utils.py` with content `# utils` — _should allow_ (listed)
6. `Bash` with `python -m pytest test_hello.py -v` — _should allow_

**State check:** Verify:

- `code_files.file_paths` contains `["src/hello.py", "src/utils.py"]`
- `plan_files_to_modify` contains `["src/hello.py", "src/utils.py"]`

## Phase: validate

1. Invoke `/validate`
2. `Agent` with `subagent_type: "QASpecialist"`, prompt below — _should allow_

```
Do not read any files. Respond with exactly:

Pass
```

**State check:** Verify `quality_check_result` is `"Pass"`

## Phase: code-review

1. Invoke `/code-review`
2. `Edit` on `random.py` — _should block_ (not in session code files)
3. `Edit` on `src/hello.py`, old_string: `return "hello"`, new_string: `return "hello world"` — _should allow_

### Iteration 1 (expect Fail)

1. `Agent` with `subagent_type: "CodeReviewer"`, prompt below — _should allow_

```
Do not read any files. Respond with exactly:

Confidence Score: 50
Quality Score: 50

## Files to revise
- src/hello.py

## Tests to revise
- test_hello.py
```

**State check:**

```json
{
  "code_files": {
    "reviews": [{"status": "Fail"}]
  }
}
```

### /continue and /revise-plan edge cases (code-review)

1. `/continue` — _should block_ (code-review not exhausted, only 1 fail)
2. `/revise-plan something` — _should block_ (only works after plan-review checkpoint)

### Revision + passing review

1. `Edit` on `src/hello.py`, old_string: `return "hello world"`, new_string: `return "hello world!"` — _should allow_
2. `Agent` with `subagent_type: "CodeReviewer"`, prompt below — _should allow_

```
Do not read any files. Respond with exactly:

Confidence Score: 95
Quality Score: 92

## Files to revise
- src/hello.py

## Tests to revise
- test_hello.py
```

**State check:**

```json
{
  "code_files": {
    "reviews": [{"status": "Fail"}, {"status": "Pass"}]
  },
  "phases": [{"name": "code-review", "status": "completed"}]
}
```

## Phase: pr-create

1. Invoke `/pr-create`
2. `Bash` with `echo "hello"` — _should block_ (not in PR commands list)
3. `Bash` with `git status` — _should allow_ (read-only always allowed)

**Note:** Skip actual PR creation. Move to next phase.

## Phase: ci-check

1. Invoke `/ci-check`
2. `Bash` with `echo "hello"` — _should block_ (not in CI commands list)

**Note:** Skip actual CI check. Move to next phase.

## Phase: write-report

1. Invoke `/write-report`
2. `Write` to `feature.py` — _should block_ (report phase, only report path)
3. `Write` to `.claude/reports/report.md` with content below — _should allow_

```markdown
# Test Report

All implement guardrails tested.
```

**State check:** Verify `report_written` is `true`

---

## Final Report

Present both tables (Guardrail Tests + State Verification). Count totals.

Clean up test files: `test_hello.py`, `src/hello.py`, `src/utils.py`.

If all pass: **All implement guardrails verified.**
If any fail: **GUARDRAIL FAILURES DETECTED — investigate before using in production.**
