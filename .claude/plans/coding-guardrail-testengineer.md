# Plan: Revise coding_guardrail.py for TestEngineer TDD Gate

## Context

`coding_guardrail.py` enforces a post-plan coding workflow. Its current TDD phase sequence is
`write-tests → write-code → validate → pr-create → completed`. The `write-tests` phase currently
gates on `TestReviewer`, but the requirement is that `test-engineer` must author tests first,
then `TestReviewer` reviews them. These are separate agents with separate responsibilities.

The fix splits `write-tests` into two phases:
- `write-tests`: `test-engineer` writes failing tests
- `review-tests`: `TestReviewer` reviews those tests

Non-TDD path is unchanged: `write-code → validate → pr-create → completed`.

**Agent name note**: The test engineer agent is registered as `test-engineer` (lowercase, hyphenated)
per `.claude/agents/engineers/test-engineer.md`. All `subagent_type` references use `"test-engineer"`.

---

## Approach

### New TDD phase sequence

```
write-tests → review-tests → write-code → validate → pr-create → completed
```

### Change 1 — `_default_coding_workflow(tdd)`: add iteration tracking, remove `review_called`

Add `"iteration": 0, "max_iterations": 3` to `review.tests`. Remove `"review_called"` from both
`review.tests` and `review.validation` — replaced by phase-aware stop guard (Change 6).

**New `review.tests` shape:**
```python
"tests": {
    "status": "pending",
    "last_result": None,
    "iteration": 0,
    "max_iterations": 3,
},
```

**New `review.validation` shape:**
```python
"validation": {
    "status": "pending",
    "last_result": None,
},
```

The `iteration` counter tracks completed TestReviewer cycles (one cycle = one `test-engineer`
run + one `TestReviewer` run). It increments only on TestReviewer Fail (Change 5). It does NOT
reset when test files are rewritten — the counter accumulates across the full retry loop.

### Change 2 — `_record_agent()`: add `test-engineer` branch, update TestReviewer branch

Add branch for `test-engineer`:
```python
elif agent_type == "test-engineer":
    workflow["tests"]["status"] = "in_progress"
```

The existing `TestReviewer` branch sets `review_called = True` and `status = "under_review"`.
Remove the `review_called = True` line (field removed). Keep `status = "under_review"`.

The existing `Validator` branch: remove `workflow["review"]["validation"]["review_called"] = True`
(line 114) — field no longer exists in the default schema. Keep all other lines unchanged.

### Change 3 — `_handle_agent()`: replace `write-tests` block with two phase blocks

The `write-code` block (lines 231-235) already correctly allows only `Validator` — **no change**.

**`write-tests` phase (`test-engineer` writes):**
```python
if phase == "write-tests":
    if agent_type == "Validator":
        return "block", "Validator is only allowed during validate phase"
    if agent_type == "TestReviewer":
        return "block", "TestReviewer is not allowed during write-tests phase — test-engineer must write tests first"
    if agent_type != "test-engineer":
        return "block", f"Only test-engineer is allowed during write-tests phase"
    tests_review = workflow["review"]["tests"]
    if tests_review["iteration"] >= tests_review["max_iterations"]:
        return "block", f"Max test review iterations ({tests_review['max_iterations']}) reached — manual intervention required"
    _record_agent(store, agent_type, tool_use_id)
    return "allow", ""
```

**`review-tests` phase (`TestReviewer` reviews):**
```python
if phase == "review-tests":
    if agent_type == "Validator":
        return "block", "Validator is only allowed during validate phase"
    if agent_type == "test-engineer":
        return "block", "test-engineer is not allowed during review-tests phase"
    if agent_type != "TestReviewer":
        return "block", f"Only TestReviewer is allowed during review-tests phase"
    if workflow["tests"].get("status") not in {"created", "failing"}:
        return "block", "Tests must be written by test-engineer before TestReviewer can run"
    tests_review = workflow["review"]["tests"]
    if tests_review["iteration"] >= tests_review["max_iterations"]:
        return "block", f"Max test review iterations ({tests_review['max_iterations']}) reached — manual intervention required"
    _record_agent(store, agent_type, tool_use_id)
    return "allow", ""
```

Note: `"in_progress"` is excluded from the `review-tests` precondition set. Only `"created"` and
`"failing"` are valid — `test-engineer` must have completed (SubagentStop fired, status set to
`"created"`) before TestReviewer can be launched.

### Change 4 — `_handle_write_or_edit()`: add `review-tests` block + fix stale messages

**Add `review-tests` block** (after write-tests block):
```python
if phase == "review-tests":
    return "block", "Cannot write files during review-tests phase — TestReviewer is read-only"
```

**Fix stale error messages in `write-tests` block** (lines 162-164). Replace the two
TestReviewer-centric messages with a single phase-aware message. The `files_created` list
append logic in lines 166-178 must be preserved unchanged:
```python
if not is_test_file:
    return "block", "Cannot write implementation code before tests are written and reviewed (complete write-tests → review-tests first)"
```

**Fix `write-code` TDD guard** (lines 182-187): replace `review_called` check with `last_result`:
```python
if workflow.get("TDD", False):
    tests_review = workflow["review"]["tests"]
    if tests_review.get("last_result") != "Pass":
        return "block", "Cannot write implementation code before TestReviewer has passed"
```

### Change 5 — `_handle_subagent_stop()`: add `test-engineer` handler, update `TestReviewer`

**Add `test-engineer` handler** (before TestReviewer block):
```python
if agent_type == "test-engineer":
    coding["tests"]["status"] = "created"
    coding["phase"] = "review-tests"
```

**Update TestReviewer handler** with iteration increment and `failed` terminal phase:
```python
if agent_type == "TestReviewer":
    review = coding["review"]["tests"]
    if verdict == "Pass":
        review["status"] = "approved"
        review["last_result"] = "Pass"
        coding["tests"]["status"] = "approved"
        coding["phase"] = "write-code"
    else:
        review["status"] = "failing"
        review["last_result"] = "Fail"
        coding["tests"]["status"] = "failing"
        review["iteration"] = review.get("iteration", 0) + 1
        if review["iteration"] >= review.get("max_iterations", 3):
            coding["phase"] = "failed"
            review["status"] = "max_iterations_reached"
        else:
            coding["phase"] = "write-tests"
```

### Change 6 — `_handle_stop()`: replace `review_called` with phase-aware check + handle `failed`

Replace lines 331-338:
```python
if workflow.get("TDD", False):
    phase = workflow.get("phase")
    tests_review = workflow["review"]["tests"]
    if phase == "failed":
        reasons.append("max test review iterations reached — manual intervention required")
    elif phase in {"write-tests", "review-tests"}:
        reasons.append("test writing/review is not yet complete")
    elif tests_review.get("last_result") == "Fail":
        reasons.append("tests are failing")
    elif tests_review.get("last_result") != "Pass":
        reasons.append("tests are not approved")
```

---

## Files to Modify

### 1. `.claude/hooks/workflow/coding_guardrail.py`

| Lines | Change |
|-------|--------|
| 41-51 | Remove `review_called` from `review.tests` and `review.validation`; add `iteration: 0, max_iterations: 3` to `review.tests` |
| 108-110 | Remove `review_called = True` from TestReviewer branch; add `test-engineer` branch |
| 159-179 | Fix stale error messages (preserve `files_created` append logic); add `review-tests` block after |
| 182-187 | Replace `review_called` check with `last_result` check |
| 215-223 | Replace `write-tests` block with `write-tests` + `review-tests` blocks |
| 249-264 | Add `test-engineer` handler before TestReviewer; update TestReviewer Fail path with iteration + `failed` phase |
| 331-338 | Replace `review_called` check with phase-aware check including `failed` phase |

### 2. `.claude/hooks/workflow/tests/test_coding_guardrail.py`

**Update `make_coding_workflow()`:**
- Remove `tests_review_called` and `validation_review_called` parameters
- Add `tests_review_iteration: int = 0` and `tests_review_max_iterations: int = 3`
- Update returned dict: no `review_called` fields; add `iteration`/`max_iterations` to `review.tests`

**Existing tests requiring updates** (explicit enumeration):

| Test | Line | Fix |
|------|------|-----|
| `test_blocks_code_write_before_review_called` | L241 | Remove `tests_review_called=False`; assert `"complete" in reason.lower()` |
| `test_blocks_code_write_after_failed_review` | L259 | Remove `tests_review_called=True`; change `assert "Fail" in reason` to `assert "complete" in reason.lower()` |
| `test_allows_code_write_after_passed_review` | L278 | Remove `tests_review_called=True` |
| `test_allows_test_reviewer_in_test_phase` | L298 | Change fixture to `phase="review-tests"`, `tests_status="created"` |
| `test_blocks_validator_before_validate_phase` | L311 | No change needed |
| `test_test_reviewer_fail_keeps_workflow_blocked` | L327 | Change fixture to `phase="review-tests"` |
| `test_test_reviewer_pass_advances_to_write_code` | L348 | Change fixture to `phase="review-tests"` |
| `test_validator_fail_returns_to_write_code` | L368 | Remove `tests_review_called=True`, `validation_review_called=True` |
| `test_validator_pass_advances_to_pr_create` | L391 | Remove `tests_review_called=True`, `validation_review_called=True` |
| `test_blocks_pr_creation_before_validation_passes` | L415 | Remove `tests_review_called=True` |
| `test_post_bash_marks_pr_created` | L434 | Remove `tests_review_called=True`, `validation_review_called=True` |
| `test_stop_blocked_before_test_review_called` | L458 | Rename to `test_stop_blocked_while_in_test_phase`; assert `"not yet complete" in reason.lower()` |
| `test_stop_blocked_when_tests_are_failing` | L472 | Remove `tests_review_called=True` |
| `test_stop_blocked_when_validation_failing` | L491 | Remove `tests_review_called=True`, `validation_review_called=True` |
| `test_stop_allowed_once_everything_complete` | L513 | Remove `tests_review_called=True`, `validation_review_called=True` |

**New tests to add:**

```
TestAgentGuard:
  test_blocks_test_reviewer_in_write_tests_phase
    — phase=write-tests, agent=TestReviewer → block, "review-tests" in reason

  test_allows_test_engineer_in_write_tests_phase
    — phase=write-tests, agent=test-engineer, tests_status=pending → allow

  test_blocks_test_engineer_in_review_tests_phase
    — phase=review-tests, agent=test-engineer → block

  test_allows_test_reviewer_in_review_tests_phase
    — phase=review-tests, agent=TestReviewer, tests_status="created" → allow

  test_blocks_test_reviewer_when_tests_not_written
    — phase=review-tests, tests_status="pending" → block

  test_blocks_test_engineer_at_max_iterations
    — phase=write-tests, tests_review_iteration=3, tests_review_max_iterations=3 → block

TestSubagentStop:
  test_test_engineer_stop_advances_to_review_tests
    — SubagentStop(test-engineer), phase=write-tests
    → phase="review-tests", tests.status="created"

  test_test_reviewer_fail_increments_iteration
    — SubagentStop(TestReviewer, "Fail"), phase=review-tests, iteration=0
    → phase="write-tests", review.tests.iteration==1

  test_test_reviewer_fail_at_max_iterations_sets_failed_phase
    — SubagentStop(TestReviewer, "Fail"), phase=review-tests, iteration=2, max_iterations=3
    → phase="failed", review.tests.status=="max_iterations_reached"

  test_stop_blocked_when_phase_is_failed
    — phase=failed → block, "manual intervention" in reason

TestWriteGuard:
  test_blocks_write_during_review_tests_phase
    — phase=review-tests, file=tests/test_app.py → block

TestDispatch:
  test_initializes_coding_workflow_with_iteration_fields
    — ExitPlanMode, TDD=true
    → review.tests.iteration==0, max_iterations==3, "review_called" not in review.tests
```

### 3. `.claude/hooks/workflow/dry_runs/coding_dry_run.py`

Replace the TDD Gate section (lines 174-238) with the new two-agent sequence:

```
--- Activation ---
PostToolUse ExitPlanMode → allow (phase=write-tests)

--- TDD Gate ---
Write /project/src/app.py in write-tests         → block
Launch TestReviewer in write-tests               → block (NEW)
Launch test-engineer [t1]                        → allow
Write /project/tests/test_app.py (by test-engineer) → allow (tests.status=created)
SubagentStop(test-engineer)                      → allow (phase=review-tests)
Launch TestReviewer [t1] in review-tests         → allow
SubagentStop(TestReviewer, "Fail")               → allow (phase=write-tests, iteration=1)
Session stop while in write-tests               → block
Write /project/src/app.py while in write-tests   → block
Launch test-engineer [t2]                        → allow
Write /project/tests/test_app.py (rewrite)       → allow
SubagentStop(test-engineer)                      → allow (phase=review-tests)
Launch TestReviewer [t2]                         → allow
SubagentStop(TestReviewer, "Pass")               → allow (phase=write-code)

--- Implementation --- (unchanged)
--- Validation --- (unchanged)
--- PR Creation --- (unchanged)
--- Completion --- (unchanged)
```

---

## Verification

```bash
python3 -m pytest .claude/hooks/workflow/tests/test_coding_guardrail.py -v
python3 .claude/hooks/workflow/dry_runs/coding_dry_run.py --tdd
python3 .claude/hooks/workflow/dry_runs/coding_dry_run.py
```

All existing tests pass (with fixture updates). New tests pass. Both dry runs complete green.
