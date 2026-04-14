---
name: test-build
description: Live E2E test of build workflow guardrails
allowed-tools: Bash, Read, Glob, Grep, Write, Edit, Agent, WebFetch
model: haiku
---

You are a **guardrail test runner**. Systematically test every guardrail by deliberately doing wrong things first (which MUST be blocked), then doing the correct thing to advance.

## Workflow Initialization

!`python3 '${CLAUDE_PLUGIN_ROOT}/scripts/utils/initializer.py' build ${CLAUDE_SESSION_ID} --tdd --test test guardrails`

## Rules

- When you get blocked, that is the **expected** outcome. Record it as PASS.
- If a step marked "should block" is NOT blocked, record it as FAIL.
- All subagents must exit immediately — no real work. Every agent prompt: "Do not read any files. Respond with exactly: ..." followed by the required output format.
- After each phase, read `state.jsonl` for your session and compare against the expected JSON. Record mismatches as FAIL.
- After each phase that has blocks, read `.claude/logs/violations.md` and verify each block produced a violation entry. Record missing entries as FAIL.
- Write results to `.claude/reports/E2E_TEST_REPORT.md` after each phase. This file is always writable in test mode.
- The state file is at: `'${CLAUDE_PLUGIN_ROOT}/scripts/state.jsonl'`
- The violations log is at: `.claude/logs/violations.md`
- **IMPORTANT**: If you are completely blocked, use `/continue` to skip the blocked phase.
- **IMPORTANT**: Direct manipulation of `state.jsonl` is allowed only once — during the plan-review reset step. All other state changes must go through the normal workflow.
- **IMPORTANT**: If bugs are found, write it in the E2E_TEST_REPORT.md file. Do not try to fix them. Fixing them is a violation of the test.

- **IMPORTANT**: Your role is to test, report and document the bugs, not to fix them.
- **IMPORTANT**: `test-build` is only triggered by the user. Start with `explore` and `research` phases in parallel.

## Report Format

Present three tables at the end:

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

**Violations Log:**

```
| Phase | Tool | Action | Logged | Result |
|-------|------|--------|--------|--------|
```

For each block that occurred, verify a matching row exists in `.claude/logs/violations.md` with the correct Phase, Tool, and Action. Mark PASS if found, FAIL if missing.

---

**IMPORTANT**: Make sure to read the file first before editing it.
**IMPORTANT**: Write report after each phase.

## Phase: explore + research

**IMPORTANT**: explore and research phases are expected to be completed in parallel.

Invoke `/explore` and `/research` in parallel (both skills in the same message).

1. `Write` to `test-guardrail.py` — _should block_ (read-only phase)
2. `Edit` on any file — _should block_ (read-only phase)
3. `Bash` with `echo "write attempt"` — _should block_ (not a read-only command)
4. `Agent` with `subagent_type: "Plan"` — _should block_ (wrong agent for explore)
5. `Bash` with `ls -la` — _should allow_
6. `Agent` with `subagent_type: "Explore"`, prompt: "Respond with exactly: Done." — _should allow_
7. Invoke 2 more Explore agents (total 3) with same prompt — _should allow_
8. `Agent` with `subagent_type: "Explore"`, prompt: "Respond with exactly: Done." — _should block_ (4th Explore exceeds max of 3)
9. `WebFetch` to `https://www.wikipedia.org` — _should block_ (not in safe domains)
10. `WebFetch` to `https://docs.python.org/3/` — _should allow_
11. `Agent` with `subagent_type: "Research"`, prompt: "Respond with exactly: Done." — _should allow_
12. Invoke 1 more Research agent (total 2) with same prompt — _should allow_
13. Wait for all agents to complete

**State check:**

```json
{
  "phases": [
    { "name": "explore", "status": "completed" },
    { "name": "research", "status": "completed" }
  ],
  "agents": "3 Explore (completed) + 2 Research (completed)"
}
```

**Violations check:** Read `.claude/logs/violations.md`. Verify these entries exist:

```markdown
| ... | research | Write | test-guardrail.py | ... |
| ... | research | Edit | ... | ... |
| ... | research | Bash | echo "write attempt" | ... |
| ... | research | Agent | Plan | ... |
| ... | research | Agent | Explore | ... |
| ... | research | WebFetch | https://www.wikipedia.org | ... |
```

**Note:** Violations during parallel explore+research log phase as "research" (the last-added phase). This is expected — the blocks are correct regardless of phase label.

## Phase: plan

1. `/install-deps` — _should block_ (must complete plan first, cannot skip ahead)
2. `/explore` — _should block_ (cannot go backwards)
3. Invoke `/plan`
4. `Write` to `.claude/plans/latest-plan.md` with content `x` — _should block_ (Plan agent must complete first)
5. `Agent` with `subagent_type: "Plan"`, prompt: "Respond with exactly: Done." — _should allow_
6. `Write` to `.claude/plans/latest-plan.md` with content below — _should block_ (missing required sections)

```markdown
# Plan

No sections here.
```

7. `Write` to `.claude/plans/latest-plan.md` with content below — _should block_ (Tasks must use bullets, not subsections)

```markdown
# Plan

## Dependencies

- None

## Tasks

### Task 1

Do something

## Files to Modify

| Action | Path         |
| ------ | ------------ |
| Create | src/hello.py |
```

8. `Write` to `wrong-plan.md` with any content — _should block_ (wrong path)
9. `Write` to `.claude/plans/latest-plan.md` with valid content below — _should allow_

```
# Test Plan

## Context
Testing guardrails.

## Dependencies
- None

## Tasks
- Create hello function

## Files to Modify

| Action | Path |
|--------|------|
| Create | src/hello.py |

## Verification

Run pytest.
```

10. `Write` to `.claude/contracts/latest-contracts.md` with content `# Contracts\n\nNo specs.` — _should block_ (missing ## Specifications)
11. `Write` to `.claude/contracts/latest-contracts.md` with content below — _should allow_

```markdown
# Contracts

## Specifications

| Name         | Type     | File         | Description    |
| ------------ | -------- | ------------ | -------------- |
| HelloService | function | src/hello.py | Hello function |
```

**State check:**

```json
{
  "plan": {
    "written": true,
    "file_path": ".claude/plans/latest-plan.md",
    "revised": null
  },
  "tasks": ["Create hello function"],
  "dependencies": {
    "packages": ["None"]
  },
  "contracts": {
    "names": ["HelloService"],
    "file_path": ".claude/contracts/latest-contracts.md"
  },
  "contract_files": ["src/hello.py"]
}
```

**Violations check:**

```markdown
| ... | install-deps | Skill | install-deps | ... |
| ... | explore | Skill | explore | ... |
| ... | plan | Write | .claude/plans/latest-plan.md | ... |
| ... | plan | Write | .claude/plans/latest-plan.md | ... |
| ... | plan | Write | .claude/plans/latest-plan.md | ... |
| ... | plan | Write | wrong-plan.md | ... |
| ... | plan | Write | .claude/contracts/latest-contracts.md | ... |
```

**IMPORTANT**: Write report after this phase.

## Phase: plan-review

1. Invoke `/plan-review`
2. `Edit` on any existing non-plan file (e.g. `claudeguard/scripts/stop.py`) — _should block_ (only plan file editable)
3. `Write` to `anything.py` — _should block_ (docs-edit phase, no writes)
4. `Edit` on `.claude/plans/latest-plan.md`, old*string: "Testing guardrails", new_string: "Testing the guardrail system" — \_should allow*

### Iteration 1 (expect Fail)

1. `Agent` with `subagent_type: "PlanReview"`, prompt below — _should allow_

```
Do not read any files. Respond with exactly:

Confidence Score: 50
Quality Score: 60
```

**State check:**

```json
{
  "plan": {
    "reviews": [
      {
        "scores": { "confidence_score": 50, "quality_score": 60 },
        "status": "Fail"
      }
    ],
    "revised": false
  }
}
```

2. `Agent` with `subagent_type: "PlanReview"` — _should block_ (plan must be revised first)
3. `Edit` on `.claude/plans/latest-plan.md`, old*string: "Testing the guardrail system", new_string: "Testing the guardrail system — revised" — \_should allow*

**State check:**

```json
{
  "plan": { "revised": true }
}
```

### Iteration 2 (expect Fail)

1. `Agent` with `subagent_type: "PlanReview"`, prompt below — _should allow_

```
Do not read any files. Respond with exactly:

Confidence Score: 70
Quality Score: 75
```

2. `Edit` on `.claude/plans/latest-plan.md`, old*string: "revised", new_string: "revised again" — \_should allow*

### Iteration 3 (expect discontinue)

1. `Agent` with `subagent_type: "PlanReview"`, prompt below — _should allow_

```
Do not read any files. Respond with exactly:

Confidence Score: 60
Quality Score: 60
```

**State check:**

```json
{
  "plan": {
    "reviews": [
      { "status": "Fail" },
      { "status": "Fail" },
      { "status": "Fail" }
    ]
  }
}
```

### Recovery via /plan-approved (exhaustion)

1. `/continue` — _should block_ (use /plan-approved for plan-review)
2. `/plan-approved` — _should allow_ (approves exhausted plan-review, proceeds to next phase)

**State check:**

```json
{
  "phases": [
    { "name": "plan-review", "status": "completed" },
    { "name": "create-tasks", "status": "in_progress" }
  ]
}
```

**Reset plan-review state for checkpoint/revise-plan flow:**

`/reset-plan-review`

### Passing review (checkpoint)

1. `Agent` with `subagent_type: "PlanReview"`, prompt below — _should allow_

```
Do not read any files. Respond with exactly:

Confidence Score: 95
Quality Score: 95
```

Workflow **discontinues** at checkpoint — this is expected.

### /revise-plan happy path

1. `/revise-plan fix the approach` — _should allow_ (reopens plan-review, resets review count)

**State check:**

```json
{
  "phases": [{ "name": "plan-review", "status": "in_progress" }],
  "plan": { "revised": false, "reviews": [] }
}
```

2. `Agent` with `subagent_type: "PlanReview"` — _should block_ (must edit plan first)
3. `Edit` on `.claude/plans/latest-plan.md`, old*string: "Testing guardrails", new_string: "Testing guardrails — user revised" — \_should allow*
4. `Agent` with `subagent_type: "PlanReview"`, prompt below — _should allow_

```
Do not read any files. Respond with exactly:

Confidence Score: 95
Quality Score: 95
```

Workflow **discontinues** again at checkpoint.

### /plan-approved and edge cases

1. `/plan-approved` — _should allow_ (resume after checkpoint, auto-starts create-tasks)

**State check:**

```json
{
  "phases": [
    { "name": "plan-review", "status": "completed" },
    { "name": "create-tasks", "status": "in_progress" }
  ]
}
```

2. `/revise-plan more changes` — _should block_ (current phase is create-tasks, not plan-review)

**Violations check:**

```markdown
| ... | plan-review | Edit | (non-plan file) | ... |
| ... | plan-review | Write | anything.py | ... |
| ... | plan-review | Agent | PlanReview | ... |
| ... | continue | Skill | continue | ... |
| ... | plan-review | Agent | PlanReview | ... |
| ... | revise-plan | Skill | revise-plan | ... |
```

**IMPORTANT**: Write report after this phase.

## Phase: create-tasks (AUTO)

Auto-starts after plan-review. Verify by reading state.

1. `TaskCreate` with subject: "Deploy to production", description: "Ship it" — _should block_ (does not match any planned task)
3. `TaskCreate` with subject: "", description: "Something" — _should block_ (empty subject)
4. `TaskCreate` with subject: "Create hello function", description: "" — _should block_ (empty description)
5. `TaskCreate` with subject: "Create hello function", description: "Implement the hello() function" — _should allow_

**State check:**

```json
{
  "created_tasks": ["Create hello function"],
  "phases": [{ "name": "create-tasks", "status": "completed" }]
}
```

**Violations check:**

```markdown
| ... | create-tasks | TaskCreate | Deploy to production | ... |
| ... | create-tasks | TaskCreate | | ... |
| ... | create-tasks | TaskCreate | Create hello function | ... |
```

Note: Row 3 has empty Action (empty subject). Row 4 has subject but empty description.

**IMPORTANT**: Write report after this phase.

## Phase: install-deps

1. Invoke `/install-deps`
2. `Write` to `app.py` — _should block_ (only package manager files)
3. `Bash` with `echo "not an install"` — _should block_ (not an install command)
4. `Write` to `requirements.txt` with content `# test deps` — _should allow_
5. `Bash` with `pip install -r requirements.txt` — _should allow_

**State check:**

```json
{
  "dependencies": { "installed": true }
}
```

**Violations check:**

```markdown
| ... | install-deps | Write | app.py | ... |
| ... | install-deps | Bash | echo "not an install" | ... |
```

**IMPORTANT**: Write report after this phase.

## Phase: define-contracts

1. Invoke `/define-contracts`
2. `Write` to `notes.md` — _should block_ (not in contracts file list)
3. `Write` to `src/random.py` with content `x = 1` — _should block_ (not in contracts file list)
4. `Write` to `src/hello.py` with content below — _should allow_ (listed in contracts, contains contract name)

```python
def HelloService(): return "hello"
```

**State check:**

```json
{
  "contracts": {
    "written": true,
    "validated": true,
    "code_files": ["src/hello.py"]
  },
  "phases": [{ "name": "define-contracts", "status": "completed" }]
}
```

**Violations check:**

```markdown
| ... | define-contracts | Write | notes.md | ... |
| ... | define-contracts | Write | src/random.py | ... |
```

**IMPORTANT**: Write report after this phase.

## Phase: write-tests (AUTO)

Auto-starts after define-contracts completes. Verify by reading `state.jsonl` — write-tests should be `in_progress`.

1. `Write` to `app.py` — _should block_ (test files only)
3. `Write` to `test_hello.py` with content below — _should allow_

```python
def test_hello():
    from hello import hello
    assert hello() is None
```

4. `Bash` with `python -m pytest test_hello.py -v` — _should allow_

**State check:**

```json
{
  "tests": {
    "file_paths": ["test_hello.py"],
    "executed": true
  },
  "phases": [{ "name": "write-tests", "status": "completed" }]
}
```

**Violations check:**

```markdown
| ... | write-tests | Write | app.py | ... |
```

**IMPORTANT**: Write report after this phase.

## Phase: test-review

1. Invoke `/test-review`
2. `Edit` on any existing non-test file (e.g. `claudeguard/scripts/stop.py`) — _should block_ (not a test file in session)
3. `Edit` on `test_hello.py`, old*string: `assert hello() is None`, new_string: `assert hello() is None  # verified` — \_should allow*

### Iteration 1 (expect Fail)

1. `Agent` with `subagent_type: "TestReviewer"`, prompt below — _should allow_

```
Do not read any files. Respond with exactly:

## Files to revise
- test_hello.py

Fail
```

**State check:**

```json
{
  "tests": {
    "reviews": [{ "verdict": "Fail" }]
  }
}
```

### Revision + passing review

1. `Edit` on `test_hello.py`, old*string: `assert hello() is None  # verified`, new_string: `assert hello() is None  # revised` — \_should allow*
2. `Agent` with `subagent_type: "TestReviewer"`, prompt below — _should allow_

```
Do not read any files. Respond with exactly:

## Files to revise
- test_hello.py

Pass
```

**State check:**

```json
{
  "tests": {
    "reviews": [{ "verdict": "Fail" }, { "verdict": "Pass" }]
  },
  "phases": [{ "name": "test-review", "status": "completed" }]
}
```

**Violations check:**

```markdown
| ... | test-review | Edit | (non-test file) | ... |
```

**IMPORTANT**: Write report after this phase.

## Phase: write-code (AUTO)

Auto-starts after test-review passes. Verify by reading `state.jsonl` — write-code should be `in_progress`.

1. `Write` to `readme.md` — _should block_ (code files only)
3. `Write` to `src/hello.py` with content below — _should allow_

```python
def hello(): return "hello"
```

4. `Bash` with `python -m pytest test_hello.py -v` — _should allow_

**State check:**

```json
{
  "code_files": {
    "file_paths": ["src/hello.py"]
  },
  "phases": [{ "name": "write-code", "status": "completed" }]
}
```

**Violations check:**

```markdown
| ... | write-code | Write | readme.md | ... |
```

**IMPORTANT**: Write report after this phase.

## Phase: quality-check

1. Invoke `/quality-check`

### Iteration 1 (expect Fail)

1. `Agent` with `subagent_type: "QASpecialist"`, prompt below — _should allow_

```
Do not read any files. Respond with exactly:

Fail
```

**State check:**

```json
{
  "quality_check_result": "Fail"
}
```

### Passing review

1. `Agent` with `subagent_type: "QASpecialist"`, prompt below — _should allow_

```
Do not read any files. Respond with exactly:

Pass
```

**State check:**

```json
{
  "quality_check_result": "Pass"
}
```

**IMPORTANT**: Write report after this phase.

## Phase: code-review

1. Invoke `/code-review`
2. `Edit` on any existing non-code-session file (e.g. `claudeguard/scripts/stop.py`) — _should block_ (not in session code files)
3. `Edit` on `src/hello.py`, old*string: `return "hello"`, new_string: `return "hello world"` — \_should allow*

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
    "reviews": [{ "status": "Fail" }]
  }
}
```

### /revise-plan edge case (code-review)

1. `/revise-plan something` — _should block_ (only works during plan-review phase)

### Revision + passing review

1. `Edit` on `src/hello.py`, old*string: `return "hello world"`, new_string: `return "hello world!"` — \_should allow*
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
    "reviews": [{ "status": "Fail" }, { "status": "Pass" }]
  },
  "phases": [{ "name": "code-review", "status": "completed" }]
}
```

**Violations check:**

```markdown
| ... | code-review | Edit | (non-session file) | ... |
| ... | revise-plan | Skill | revise-plan | ... |
```

**IMPORTANT**: Write report after this phase.

## Phase: pr-create

1. Invoke `/pr-create`
2. `Bash` with `echo "hello"` — _should block_ (not in PR commands list)
3. `Bash` with `gh pr create --title test` — _should block_ (missing --json flag)
4. `Bash` with `git status` — _should allow_ (read-only always allowed)

**Note:** Skip actual PR creation. Move to next phase.

**Violations check:**

```markdown
| ... | pr-create | Bash | echo "hello" | ... |
| ... | pr-create | Bash | gh pr create --title test | ... |
```

**IMPORTANT**: Write report after this phase.

## Phase: ci-check

1. Invoke `/ci-check`
2. `Bash` with `echo "hello"` — _should block_ (not in CI commands list)
3. `Bash` with `gh pr checks` — _should block_ (missing --json flag)

**Note:** Skip actual CI check. Move to next phase.

**Violations check:**

```markdown
| ... | ci-check | Bash | echo "hello" | ... |
| ... | ci-check | Bash | gh pr checks | ... |
```

**IMPORTANT**: Write report after this phase.

## Stop hook

Before entering write-report, the workflow is incomplete. Attempting to stop should be blocked.

1. Attempt to stop (present final message without invoking `/write-report`) — _should block_ (not all phases completed)

## Phase: write-report

1. Invoke `/write-report`
2. `Write` to `feature.py` — _should block_ (report phase, only report path)
3. `Write` to `.claude/reports/report.md` with content below — _should allow_

```markdown
# Test Report

All guardrails tested.
```

**State check:**

```json
{
  "report_written": true
}
```

**Violations check:**

```markdown
| ... | write-report | Write | feature.py | ... |
```

---

## Final Report

1. Present all three tables (Guardrail Tests + State Verification + Violations Log). Count totals.
2. Clean up test files: `test_hello.py`, `src/hello.py`, `requirements.txt`.

If all pass: **All build guardrails verified.**
If any fail: **GUARDRAIL FAILURES DETECTED — investigate before using in production.**
