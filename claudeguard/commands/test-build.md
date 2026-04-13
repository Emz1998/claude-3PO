---
name: test-build
description: Live E2E test of build workflow guardrails
allowed-tools: Bash, Read, Glob, Grep, Write, Edit, Agent, WebFetch
model: haiku
---

You are a **guardrail test runner**. Your job is to systematically test every guardrail by deliberately doing wrong things first (which MUST be blocked), then doing the correct thing to advance.

## Workflow Initialization

!`python3 '${CLAUDE_PLUGIN_ROOT}/scripts/utils/initializer.py' build ${CLAUDE_SESSION_ID} --tdd test guardrails`

## How This Works

1. At each phase, you will attempt **forbidden actions** that should be blocked by the guardrails.
2. After each block, record it as a **PASS** (block was expected).
3. If a forbidden action is NOT blocked, record it as a **FAIL**.
4. Then perform the **correct action** to advance to the next phase.
5. At the end, present a test report.

**Important**: When you get blocked, that is the EXPECTED outcome. Do NOT treat blocks as errors. Record them as passing tests.

**Important**: All subagents must exit immediately. Do NOT let them do real work — we are testing guardrails, not functionality. Every agent prompt must instruct the agent to respond with ONLY the required output format (scores, verdicts, etc.) and nothing else. Keep prompts under 2 sentences. Example: "Do not read any files. Respond with exactly: Confidence Score: 95\nQuality Score: 95"

## Test Report Format

Track results in this format and present at the end:

```
| Phase | Test | Expected | Actual | Result |
|-------|------|----------|--------|--------|
| explore | Write file | BLOCK | BLOCK | PASS |
```

---

## Test Sequence

Execute each step in order. For each "TRY" step, attempt the action. For each "DO" step, perform the correct action.

### explore + research (parallel)

**Start**: Invoke `/explore` and `/research` in parallel (both as skills in the same message).

**TRY (expect BLOCK) — explore guards:**
- Write a file: `Write` to `test-guardrail.py` — should block (read-only phase)
- Edit a file: `Edit` on any file — should block (read-only phase)
- Run a non-read-only command: `Bash` with `echo "write attempt"` — should block (not a read-only command)
- Invoke wrong agent: `Agent` with `subagent_type: "Plan"` — should block (expected: Explore)

**TRY (expect ALLOW) — explore guards:**
- Read-only command: `Bash` with `ls -la` — should allow
- Correct agent: `Agent` with `subagent_type: "Explore"`, description: "Test", prompt: "Respond with exactly: Done." — should allow

**DO**: Invoke 2 more Explore agents (total 3) with the same minimal prompt.

**TRY (expect BLOCK) — webfetch guards:**
- WebFetch unlisted domain: `WebFetch` to `https://www.wikipedia.org` — should block (not in safe domains list)

**TRY (expect ALLOW) — webfetch guards:**
- WebFetch safe domain: `WebFetch` to `https://docs.python.org/3/` — should allow
- Research agent: `Agent` with `subagent_type: "Research"`, description: "Test", prompt: "Respond with exactly: Done." — should allow

**DO**: Invoke 1 more Research agent (total 2) with the same minimal prompt. Wait for all agents to complete.

### plan

**TRY (expect BLOCK) — phase ordering:**
- Skip to `/install-deps` — should block (must complete plan first)
- Re-invoke `/explore` — should block (cannot go backwards)

**DO**: Invoke `/plan` to enter plan phase.

**TRY (expect BLOCK) — write guard:**
- Write plan before Plan agent completes: `Write` to `.claude/plans/latest-plan.md` — should block (Plan agent must complete first)

**DO**: Invoke `Agent` with `subagent_type: "Plan"`, description: "Test", prompt: "Respond with exactly: Done." — wait for completion.

**TRY (expect BLOCK) — plan content validation:**
- Write plan with missing sections: `Write` to `.claude/plans/latest-plan.md` with content `# Plan\nNo sections here.` — should block (missing required sections)
- Write plan with Tasks as subsections: `Write` to `.claude/plans/latest-plan.md` with content `# Plan\n\n## Dependencies\n- None\n\n## Contracts\n- None\n\n## Tasks\n\n### Task 1\nDo something\n` — should block (Tasks must use bullets)
- Write to wrong path: `Write` to `wrong-plan.md` — should block (wrong path)

**TRY (expect ALLOW):**
- Write valid plan: `Write` to `.claude/plans/latest-plan.md` with this content:

```
# Test Plan

## Context
Testing guardrails.

## Dependencies
- None

## Contracts
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

### plan-review

**DO**: Invoke `/plan-review`.

**TRY (expect BLOCK):**
- Edit wrong file: `Edit` on `wrong.md` — should block (only plan file editable)
- Write a file: `Write` to `anything.py` — should block (docs-edit phase, no writes)

**TRY (expect ALLOW):**
- Edit plan file: `Edit` on `.claude/plans/latest-plan.md`, old_string: "Testing guardrails", new_string: "Testing the guardrail system" — should allow

**DO**: Invoke `Agent` with `subagent_type: "PlanReview"`, description: "Test", prompt: "Do not read any files. Respond with exactly:\n\nConfidence Score: 95\nQuality Score: 95"

Wait for completion. The workflow should **discontinue** (checkpoint). This is expected.

### install-deps

**DO**: Invoke `/install-deps`.

**TRY (expect BLOCK):**
- Write code file: `Write` to `app.py` — should block (only package manager files)
- Run non-install command: `Bash` with `echo "not an install"` — should block

**TRY (expect ALLOW):**
- Write package manager file: `Write` to `requirements.txt` with content `# test deps` — should allow
- Run install command: `Bash` with `pip install -r requirements.txt` — should allow (records deps installed)

### define-contracts

**DO**: Invoke `/define-contracts`.

**TRY (expect BLOCK):**
- Write markdown: `Write` to `notes.md` — should block (code files only)

**TRY (expect ALLOW):**
- Write code file: `Write` to `src/hello.py` with content `def hello(): pass` — should allow

**DO**: Write contracts file to complete the phase:
- `Write` to `.claude/contracts/latest-contracts.md` with content `- None`

### write-tests (AUTO)

After define-contracts completes, write-tests should auto-start.

**TRY (expect BLOCK):**
- Invoke `/write-tests` as skill — should block (auto-phase)
- Write non-test file: `Write` to `app.py` — should block (test files only)

**TRY (expect ALLOW):**
- Write test file: `Write` to `test_hello.py` with content:
```python
def test_hello():
    from hello import hello
    assert hello() is None
```
- Run tests: `Bash` with `python -m pytest test_hello.py -v` — should allow

### test-review

**DO**: Invoke `/test-review`.

**TRY (expect BLOCK):**
- Edit unknown file: `Edit` on `unknown.py` — should block (not a test file in session)

**TRY (expect ALLOW):**
- Edit test file: `Edit` on `test_hello.py`, old_string: `assert hello() is None`, new_string: `assert hello() is None  # verified` — should allow

**DO**: Invoke `Agent` with `subagent_type: "TestReviewer"`, description: "Test", prompt: "Do not read any files. Respond with exactly:\n\n## Files to revise\n- test_hello.py\n\nPass"

### write-code (AUTO)

After test-review passes, write-code should auto-start.

**TRY (expect BLOCK):**
- Invoke `/write-code` as skill — should block (auto-phase)
- Write markdown: `Write` to `readme.md` — should block (code files only)

**TRY (expect ALLOW):**
- Write code file: `Write` to `src/hello.py` with content `def hello(): return "hello"` — should allow
- Run tests: `Bash` with `python -m pytest test_hello.py -v` — should allow

### quality-check

**DO**: Invoke `/quality-check`.

**DO**: Invoke `Agent` with `subagent_type: "QASpecialist"`, description: "Test", prompt: "Do not read any files. Respond with exactly:\n\nPass"

### code-review

**DO**: Invoke `/code-review`.

**TRY (expect BLOCK):**
- Edit file not in session: `Edit` on `random.py` — should block

**TRY (expect ALLOW):**
- Edit code file in session: `Edit` on `src/hello.py`, old_string: `return "hello"`, new_string: `return "hello world"` — should allow

**DO**: Invoke `Agent` with `subagent_type: "CodeReviewer"`, description: "Test", prompt: "Do not read any files. Respond with exactly:\n\nConfidence Score: 95\nQuality Score: 92\n\n## Files to revise\n- src/hello.py\n\n## Tests to revise\n- test_hello.py"

### pr-create

**DO**: Invoke `/pr-create`.

**TRY (expect BLOCK):**
- PR create without --json: `Bash` with `gh pr create --title test` — should block

**TRY (expect ALLOW):**
- Git read command: `Bash` with `git status` — should allow (read-only always allowed)

**Note**: Skip actual PR creation. Move to next phase.

### ci-check

**DO**: Invoke `/ci-check`.

**TRY (expect BLOCK):**
- CI check without --json: `Bash` with `gh pr checks` — should block

**Note**: Skip actual CI check. Move to next phase.

### write-report

**DO**: Invoke `/write-report`.

**TRY (expect BLOCK):**
- Write code file: `Write` to `feature.py` — should block (report phase, only report path)

**TRY (expect ALLOW):**
- Write report: `Write` to `.claude/reports/report.md` with content `# Test Report\n\nAll guardrails tested.` — should allow

---

## Final Report

Present the test results table. Count total tests, PASS, and FAIL.

Clean up any test files created (`test_hello.py`, `src/hello.py`, `requirements.txt`).

If all tests pass: **All build guardrails verified.**
If any fail: **GUARDRAIL FAILURES DETECTED — investigate before using in production.**
